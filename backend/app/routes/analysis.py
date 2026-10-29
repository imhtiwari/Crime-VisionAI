import json
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from app.extensions import db
from app.models import AnalysisArtifact, AnalysisRun, Detection, Evidence, ProcessingJob, TimelineEvent, TranscriptSegment
from app.services.audio_service import audio_service
from app.services.caption_service import caption_service
from app.services.detection_service import detection_service
from app.tasks.queue import submit_job
from app.utils.file_utils import validate_audio, validate_image, validate_video

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/image/<evidence_id>', methods=['POST'])
def analyze_image(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    if evidence.media_type != 'image':
        return jsonify({'error': 'Evidence is not an image.'}), 400
    valid, image_metadata = validate_image(evidence.storage_path)
    if not valid:
        return jsonify({'error': 'Evidence image is corrupt or unavailable.'}), 422

    body = request.get_json(silent=True) or {}
    confidence_threshold = body.get('confidence_threshold', current_app.config.get('DETECTION_CONFIDENCE_THRESHOLD', 0.5))
    if not isinstance(confidence_threshold, (int, float)) or not 0 <= confidence_threshold <= 1:
        return jsonify({'error': 'confidence_threshold must be a number between 0 and 1.'}), 400

    analysis = AnalysisRun(
        id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_type='image_detection',
        model_identifier=detection_service.model_name, processing_status='running',
    )
    db.session.add(analysis)
    analysis_id = analysis.id
    db.session.commit()
    db.session.add(TimelineEvent(
        id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis.id,
        title='Image analysis requested', description='An investigator initiated image metadata and configured-model analysis.',
        category='analysis_activity', source_type='analysis_execution',
        verification_status='unverified', time_basis='system_clock',
    ))
    try:
        detections = []
        detection_status = detection_service.status
        if detection_status == 'ready':
            detections = detection_service.detect_objects(evidence.storage_path, confidence_threshold)
            for result in detections:
                box = result['bbox']
                db.session.add(Detection(
                    id=str(uuid.uuid4()), analysis_run_id=analysis.id, label=result['label'],
                    confidence=result['confidence'], bbox_x1=box['x1'], bbox_y1=box['y1'],
                    bbox_x2=box['x2'], bbox_y2=box['y2'],
                ))

        try:
            caption = caption_service.caption(evidence.storage_path)
        except Exception:
            current_app.logger.exception('Local image captioning failed')
            caption = {'status': 'failed', 'text': None, 'model': caption_service.model_name}
        artifacts = []
        if detections:
            from app.services.image_service import write_annotated_image
            output_path = Path(current_app.config['DERIVED_FOLDER']) / evidence.id / f'{analysis_id}_annotated.jpg'
            output_path.parent.mkdir(parents=True, exist_ok=True)
            write_annotated_image(evidence.storage_path, detections, output_path)
            db.session.add(AnalysisArtifact(
                id=str(uuid.uuid4()), analysis_run_id=analysis_id, kind='annotated_image',
                mime_type='image/jpeg', storage_path=str(output_path.resolve()),
                metadata_json=json.dumps({'human_review_required': True}),
            ))
            artifacts.append({'kind': 'annotated_image', 'download_url': f'/api/v1/analysis/{analysis_id}/artifacts/annotated_image'})

        status = 'completed' if detection_status == 'ready' else detection_status
        analysis.processing_status = status
        analysis.model_identifier = detection_service.model_name
        analysis.model_version = detection_service.model_version
        analysis.completion_timestamp = datetime.utcnow()
        analysis.result_metadata = json.dumps({
            'image': image_metadata,
            'object_detection_status': detection_status,
            'caption': caption,
            'confidence_threshold': confidence_threshold,
            'human_review_required': True,
            'artifacts': artifacts,
        })
        db.session.add(TimelineEvent(
            id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis.id,
            title='Image analysis completed', description=f'Analysis finished with status: {status}.',
            category='analysis_activity', source_type='analysis_execution',
            verification_status='unverified', time_basis='system_clock',
        ))
        evidence.processing_status = 'analyzed' if detection_status == 'ready' else 'metadata_extracted'
        db.session.commit()
        return jsonify({
            'analysis_id': analysis_id,
            'evidence_id': evidence.id,
            'status': status,
            'image_metadata': image_metadata,
            'detector': {'model': detection_service.model_name, 'status': detection_status, 'detections': detections},
            'caption': caption,
            'artifacts': artifacts,
            'warnings': ['Automated outputs are preliminary and require human review.'],
        }), 200
    except Exception as error:
        db.session.rollback()
        analysis = db.session.get(AnalysisRun, analysis_id)
        if analysis:
            analysis.processing_status = 'failed'
            analysis.error_details = 'Image analysis failed. Check model configuration and image availability.'
            analysis.completion_timestamp = datetime.utcnow()
            db.session.add(TimelineEvent(
                id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis_id,
                title='Image analysis failed', description='The image analysis operation did not complete.',
                category='analysis_activity', source_type='analysis_execution',
                verification_status='unverified', time_basis='system_clock',
            ))
            db.session.commit()
        current_app.logger.exception('Image analysis failed')
        return jsonify({'analysis_id': analysis_id, 'status': 'failed', 'error': 'Image analysis failed.'}), 500


@analysis_bp.route('/video/<evidence_id>', methods=['POST'])
def analyze_video(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    if evidence.media_type != 'video':
        return jsonify({'error': 'Evidence is not a video.'}), 400
    valid, metadata = validate_video(evidence.storage_path)
    if not valid:
        return jsonify({'error': 'Evidence video is corrupt or cannot be decoded.'}), 422
    if metadata['duration_seconds'] and metadata['duration_seconds'] > current_app.config['MAX_VIDEO_DURATION']:
        return jsonify({'error': 'Video exceeds the configured duration limit.'}), 413
    body = request.get_json(silent=True) or {}
    interval = body.get('sampling_interval_seconds', current_app.config['VIDEO_FRAME_SAMPLE_INTERVAL'])
    if not isinstance(interval, int) or not 1 <= interval <= 600:
        return jsonify({'error': 'sampling_interval_seconds must be an integer between 1 and 600.'}), 400
    return _queue_analysis(evidence, 'video_frame_analysis', 'video', {'sampling_interval_seconds': interval})


@analysis_bp.route('/audio/<evidence_id>', methods=['POST'])
def analyze_audio(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    if evidence.media_type != 'audio':
        return jsonify({'error': 'Evidence is not audio.'}), 400
    valid, _metadata = validate_audio(evidence.storage_path)
    if not valid:
        return jsonify({'error': 'Evidence audio is corrupt or its codec is unsupported by the installed dependencies.'}), 422
    return _queue_analysis(evidence, 'audio_transcription', 'audio')


def _queue_analysis(evidence, analysis_type, job_type, options=None):
    analysis = AnalysisRun(
        id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_type=analysis_type,
        model_identifier=audio_service.model_source if job_type == 'audio' else detection_service.model_name,
        processing_status='queued',
    )
    job = ProcessingJob(
        id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis.id,
        job_type=job_type, status='queued', progress=0, message='Waiting for a worker.',
        options_json=json.dumps(options or {}),
    )
    db.session.add_all([analysis, job])
    db.session.commit()
    try:
        submit_job(current_app._get_current_object(), job.id)
    except RuntimeError as error:
        job.status = 'failed'
        job.error_details = 'The processing queue is full; retry when an active job finishes.'
        job.message = job.error_details
        job.completed_at = datetime.utcnow()
        analysis.processing_status = 'failed'
        analysis.error_details = job.error_details
        analysis.completion_timestamp = datetime.utcnow()
        db.session.commit()
        return jsonify({'error': job.error_details}), 429
    return jsonify({'analysis_id': analysis.id, 'job_id': job.id, 'status': 'queued'}), 202


@analysis_bp.route('/audio/<evidence_id>/transcript', methods=['GET'])
def get_transcript(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    analysis = AnalysisRun.query.filter_by(evidence_id=evidence.id, analysis_type='audio_transcription').order_by(AnalysisRun.creation_timestamp.desc()).first()
    if analysis is None:
        return jsonify({'error': 'No transcription analysis exists for this evidence.'}), 404
    segments = TranscriptSegment.query.filter_by(analysis_run_id=analysis.id).order_by(TranscriptSegment.start_seconds.asc()).all()
    return jsonify({
        'analysis_id': analysis.id,
        'status': analysis.processing_status,
        'metadata': json.loads(analysis.result_metadata) if analysis.result_metadata else None,
        'segments': [{
            'start_seconds': segment.start_seconds,
            'end_seconds': segment.end_seconds,
            'text': segment.text,
            'language': segment.language,
            'language_probability': segment.language_probability,
        } for segment in segments],
    })


@analysis_bp.route('/<analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    analysis = AnalysisRun.query.get_or_404(analysis_id)
    detections = Detection.query.filter_by(analysis_run_id=analysis_id).order_by(Detection.frame_number, Detection.id).all()
    return jsonify({
        'analysis_id': analysis.id,
        'evidence_id': analysis.evidence_id,
        'analysis_type': analysis.analysis_type,
        'model_identifier': analysis.model_identifier,
        'model_version': analysis.model_version,
        'processing_status': analysis.processing_status,
        'creation_timestamp': analysis.creation_timestamp.isoformat(),
        'completion_timestamp': analysis.completion_timestamp.isoformat() if analysis.completion_timestamp else None,
        'error_details': analysis.error_details,
        'result_metadata': json.loads(analysis.result_metadata) if analysis.result_metadata else None,
        'findings': [{
            'id': item.id,
            'label': item.label,
            'confidence': item.confidence,
            'frame_number': item.frame_number,
            'timestamp': item.timestamp,
            'bbox': {'x1': item.bbox_x1, 'y1': item.bbox_y1, 'x2': item.bbox_x2, 'y2': item.bbox_y2},
        } for item in detections],
    })


@analysis_bp.route('/<analysis_id>/artifacts/<kind>', methods=['GET'])
def download_analysis_artifact(analysis_id, kind):
    artifact = AnalysisArtifact.query.filter_by(analysis_run_id=analysis_id, kind=kind).first_or_404()
    path = Path(artifact.storage_path).resolve()
    derived_root = Path(current_app.config['DERIVED_FOLDER']).resolve()
    if derived_root not in path.parents or not path.is_file():
        return jsonify({'error': 'Analysis artifact is unavailable.'}), 404
    return send_file(path, mimetype=artifact.mime_type, as_attachment=True, download_name=path.name)
