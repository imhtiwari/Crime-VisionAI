import json
import math
import uuid
from datetime import datetime
from pathlib import Path

import cv2

from app.extensions import db
from app.models import AnalysisArtifact, AnalysisRun, Detection, Evidence, ProcessingJob, TimelineEvent
from app.services.detection_service import detection_service


def process_video_job(app, job_id):
    """Extract bounded, timestamped frames and run detection only when available."""
    with app.app_context():
        job = db.session.get(ProcessingJob, job_id)
        if job is None or job.status != 'queued':
            return
        analysis = db.session.get(AnalysisRun, job.analysis_run_id)
        evidence = db.session.get(Evidence, job.evidence_id)
        if analysis is None or evidence is None:
            job.status = 'failed'
            job.error_details = 'The linked evidence or analysis record is missing.'
            job.completed_at = datetime.utcnow()
            db.session.commit()
            return

        job.status = 'running'
        job.started_at = datetime.utcnow()
        job.message = 'Reading video metadata.'
        analysis.processing_status = 'running'
        db.session.add(TimelineEvent(
            id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis.id,
            title='Video sampling requested', description='A background job was started for metadata extraction and sampled-frame analysis.',
            category='analysis_activity', source_type='analysis_execution',
            verification_status='unverified', time_basis='system_clock',
        ))
        db.session.commit()

        capture = cv2.VideoCapture(evidence.storage_path)
        try:
            if not capture.isOpened():
                raise ValueError('Video decoder could not open this file.')
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if fps <= 0 or total_frames <= 0 or width <= 0 or height <= 0:
                raise ValueError('Video metadata is incomplete or invalid.')
            duration = total_frames / fps
            if duration > app.config['MAX_VIDEO_DURATION']:
                raise ValueError('Video exceeds the configured duration limit.')

            options = json.loads(job.options_json) if job.options_json else {}
            interval = max(1, int(options.get('sampling_interval_seconds', app.config['VIDEO_FRAME_SAMPLE_INTERVAL'])))
            max_frames = max(1, int(app.config['MAX_VIDEO_FRAMES']))
            sample_times = [index * interval for index in range(math.ceil(duration / interval))][:max_frames]
            artifact_root = Path(app.config['DERIVED_FOLDER']) / evidence.id / analysis.id
            artifact_root.mkdir(parents=True, exist_ok=True)
            frame_results = []
            inference_status = detection_service.status

            for index, sample_time in enumerate(sample_times):
                target_frame = min(total_frames - 1, int(round(sample_time * fps)))
                capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                timestamp = target_frame / fps
                frame_path = artifact_root / f'frame_{index + 1:04d}.jpg'
                if not cv2.imwrite(str(frame_path), frame):
                    raise OSError('Could not save an extracted video frame.')

                detections = []
                if inference_status == 'ready':
                    detections = detection_service.detect_objects(str(frame_path))
                    for result in detections:
                        box = result['bbox']
                        db.session.add(Detection(
                            id=str(uuid.uuid4()), analysis_run_id=analysis.id,
                            label=result['label'], confidence=result['confidence'],
                            bbox_x1=box['x1'], bbox_y1=box['y1'], bbox_x2=box['x2'], bbox_y2=box['y2'],
                            frame_number=target_frame, timestamp=timestamp,
                        ))

                frame_metadata = {'frame_number': target_frame, 'relative_seconds': timestamp, 'detections': detections}
                frame_results.append(frame_metadata)
                db.session.add(AnalysisArtifact(
                    id=str(uuid.uuid4()), analysis_run_id=analysis.id, kind='video_frame',
                    mime_type='image/jpeg', storage_path=str(frame_path.resolve()),
                    metadata_json=json.dumps({'frame_number': target_frame, 'relative_seconds': timestamp}),
                ))
                db.session.add(TimelineEvent(
                    id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis.id,
                    title='Frame sampled', description='A frame was extracted for analysis.',
                    category='media_sampling', source_type='extracted_metadata',
                    occurred_at=None, relative_seconds=timestamp, time_basis='media_relative',
                    verification_status='unverified',
                ))
                job.progress = min(95, int((index + 1) * 95 / max(len(sample_times), 1)))
                job.message = f'Extracted {index + 1} of {len(sample_times)} selected frames.'
                db.session.commit()

            if not frame_results:
                raise ValueError('No decodable frames were found in the video.')
            result = {
                'video': {'duration_seconds': duration, 'fps': fps, 'width': width, 'height': height,
                          'frame_count': total_frames, 'sampling_interval_seconds': interval},
                'frames': frame_results,
                'object_detection_status': inference_status,
                'limitations': ['Frame sampling does not perform action recognition or establish events.'],
            }
            analysis.result_metadata = json.dumps(result)
            analysis.model_identifier = detection_service.model_name
            analysis.model_version = detection_service.model_version
            analysis.processing_status = 'completed' if inference_status == 'ready' else 'completed_metadata_only'
            analysis.completion_timestamp = datetime.utcnow()
            evidence.processing_status = 'processed'
            db.session.add(TimelineEvent(
                id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis.id,
                title='Video sampling completed', description=f'Extracted {len(frame_results)} frames; object detection status: {inference_status}.',
                category='analysis_activity', source_type='analysis_execution',
                verification_status='unverified', time_basis='system_clock',
            ))
            job.status = 'completed'
            job.progress = 100
            job.message = f'Frame sampling complete. Object detection: {inference_status}.'
            job.completed_at = datetime.utcnow()
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            job = db.session.get(ProcessingJob, job_id)
            analysis = db.session.get(AnalysisRun, job.analysis_run_id) if job else None
            if job:
                job.status = 'failed'
                job.error_details = 'Video processing failed. Confirm the file is decodable and within configured limits.'
                job.message = 'Video processing failed.'
                job.completed_at = datetime.utcnow()
            if analysis:
                analysis.processing_status = 'failed'
                analysis.error_details = str(error)[:1000]
                analysis.completion_timestamp = datetime.utcnow()
            app.logger.exception('Video processing job failed')
            db.session.commit()
        finally:
            capture.release()
