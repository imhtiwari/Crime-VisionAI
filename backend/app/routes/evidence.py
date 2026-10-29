import os
import uuid
import mimetypes
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import AnalysisRun, AuditEvent, Evidence, TimelineEvent
from app.utils.file_utils import (
    allowed_file,
    calculate_file_hash,
    generate_internal_filename,
    get_media_type,
    validate_audio,
    validate_image,
    validate_video,
)

evidence_bp = Blueprint('evidence', __name__)


def _inspect_file(file_path, media_type):
    validators = {'image': validate_image, 'video': validate_video, 'audio': validate_audio}
    valid, metadata = validators[media_type](file_path)
    if not valid:
        return False, None
    return True, metadata


@evidence_bp.route('/upload', methods=['POST'])
def upload_evidence():
    uploaded = request.files.get('file')
    if uploaded is None:
        return jsonify({'error': 'No file provided.'}), 400
    if not uploaded.filename:
        return jsonify({'error': 'No file selected.'}), 400

    original_filename = secure_filename(uploaded.filename)
    media_type = get_media_type(original_filename)
    if not original_filename or not media_type or not allowed_file(original_filename, media_type):
        return jsonify({'error': 'Unsupported file type. Supported image, audio, and video codecs are listed by /api/v1/capabilities.'}), 400

    storage_path = Path(current_app.config['UPLOAD_FOLDER']) / generate_internal_filename(original_filename)
    try:
        uploaded.save(storage_path)
        file_size = storage_path.stat().st_size
        if file_size == 0:
            storage_path.unlink(missing_ok=True)
            return jsonify({'error': 'The uploaded file is empty.'}), 400
        valid, metadata = _inspect_file(storage_path, media_type)
        if not valid:
            storage_path.unlink(missing_ok=True)
            return jsonify({'error': 'File content is corrupt, unsupported, or does not match its media type.'}), 400

        file_hash = calculate_file_hash(storage_path)
        existing = Evidence.query.filter_by(file_hash=file_hash).first()
        if existing:
            storage_path.unlink(missing_ok=True)
            return jsonify({'error': 'File already exists.', 'evidence_id': existing.id}), 409

        evidence = Evidence(
            id=str(uuid.uuid4()),
            original_filename=original_filename,
            internal_filename=storage_path.name,
            storage_path=str(storage_path.resolve()),
            media_type=media_type,
            file_size=file_size,
            file_hash=file_hash,
            processing_status='pending',
        )
        db.session.add(evidence)
        db.session.add(TimelineEvent(
            id=str(uuid.uuid4()), evidence_id=evidence.id,
            title='Evidence uploaded', description='A file was registered in the local evidence vault.',
            category='system_activity', source_type='observed_file_record',
            verification_status='unverified', occurred_at=None,
            time_basis='upload_record_timestamp',
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        storage_path.unlink(missing_ok=True)
        current_app.logger.exception('Evidence upload failed')
        return jsonify({'error': 'Evidence could not be stored.'}), 500

    return jsonify({
        'evidence_id': evidence.id,
        'original_filename': evidence.original_filename,
        'media_type': evidence.media_type,
        'file_size': evidence.file_size,
        'file_hash': evidence.file_hash,
        'upload_timestamp': evidence.upload_timestamp.isoformat(),
        'processing_status': evidence.processing_status,
        'validated_metadata': metadata,
    }), 201


@evidence_bp.route('/', methods=['GET'], strict_slashes=False)
def list_evidence():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    if page < 1 or per_page < 1 or per_page > 100:
        return jsonify({'error': 'page must be positive and per_page must be between 1 and 100.'}), 400

    query = Evidence.query
    media_type = request.args.get('media_type')
    status = request.args.get('status')
    search = request.args.get('search', '').strip()
    if media_type:
        if media_type not in {'image', 'audio', 'video'}:
            return jsonify({'error': 'media_type must be image, audio, or video.'}), 400
        query = query.filter_by(media_type=media_type)
    if status:
        query = query.filter_by(processing_status=status)
    if search:
        query = query.filter(Evidence.original_filename.ilike(f'%{search[:100]}%'))

    page_result = query.order_by(Evidence.upload_timestamp.desc()).paginate(page=page, per_page=per_page)
    return jsonify({
        'evidence': [_evidence_summary(item) for item in page_result.items],
        'total': page_result.total,
        'pages': page_result.pages,
        'current_page': page,
        'per_page': per_page,
    })


@evidence_bp.route('/<evidence_id>', methods=['GET'])
def get_evidence(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    analyses = AnalysisRun.query.filter_by(evidence_id=evidence.id).order_by(AnalysisRun.creation_timestamp.desc()).all()
    result = _evidence_summary(evidence)
    result.update({
        'file_hash': evidence.file_hash,
        'analysis_history': [{
            'analysis_id': analysis.id,
            'analysis_type': analysis.analysis_type,
            'processing_status': analysis.processing_status,
            'creation_timestamp': analysis.creation_timestamp.isoformat(),
            'completion_timestamp': analysis.completion_timestamp.isoformat() if analysis.completion_timestamp else None,
        } for analysis in analyses],
    })
    return jsonify(result)


@evidence_bp.route('/<evidence_id>/download', methods=['GET'])
def download_evidence(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    path = Path(evidence.storage_path).resolve()
    upload_root = Path(current_app.config['UPLOAD_FOLDER']).resolve()
    if path.parent != upload_root or path.name != evidence.internal_filename or not path.is_file():
        return jsonify({'error': 'Evidence file is unavailable.'}), 404
    return send_file(path, as_attachment=True, download_name=evidence.original_filename)


@evidence_bp.route('/<evidence_id>/preview', methods=['GET'])
def preview_evidence(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    mimetypes_by_type = {'image': 'image', 'audio': 'audio', 'video': 'video'}
    if evidence.media_type not in mimetypes_by_type:
        return jsonify({'error': 'This evidence type cannot be previewed inline.'}), 400
    path = Path(evidence.storage_path).resolve()
    upload_root = Path(current_app.config['UPLOAD_FOLDER']).resolve()
    if path.parent != upload_root or path.name != evidence.internal_filename or not path.is_file():
        return jsonify({'error': 'Evidence file is unavailable.'}), 404
    mimetype = mimetypes.guess_type(evidence.original_filename)[0] or 'application/octet-stream'
    if not mimetype.startswith(f"{mimetypes_by_type[evidence.media_type]}/"):
        return jsonify({'error': 'Evidence media type does not match its filename.'}), 409
    return send_file(path, mimetype=mimetype, as_attachment=False, max_age=0, conditional=True)


@evidence_bp.route('/<evidence_id>', methods=['DELETE'])
def delete_evidence(evidence_id):
    if request.args.get('confirm') != evidence_id:
        return jsonify({'error': 'Pass confirm=<evidence_id> to confirm deletion.'}), 400
    evidence = Evidence.query.get_or_404(evidence_id)
    original_path = Path(evidence.storage_path).resolve()
    upload_root = Path(current_app.config['UPLOAD_FOLDER']).resolve()
    if original_path.parent != upload_root or original_path.name != evidence.internal_filename:
        return jsonify({'error': 'Evidence file location failed integrity validation.'}), 409

    quarantine_dir = Path(current_app.config['EVIDENCE_FOLDER']) / 'deleted'
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    quarantine_path = quarantine_dir / f'{evidence.id}_{evidence.internal_filename}'
    if original_path.exists():
        os.replace(original_path, quarantine_path)
    try:
        db.session.add(AuditEvent(
            id=str(uuid.uuid4()), action='evidence.deleted', entity_type='evidence',
            entity_id=evidence.id, details_json='{"confirmation_required": true}',
        ))
        db.session.delete(evidence)
        db.session.commit()
    except Exception:
        db.session.rollback()
        if quarantine_path.exists():
            os.replace(quarantine_path, original_path)
        current_app.logger.exception('Evidence deletion failed')
        return jsonify({'error': 'Evidence could not be deleted.'}), 500
    quarantine_path.unlink(missing_ok=True)
    return '', 204


def _evidence_summary(evidence):
    return {
        'id': evidence.id,
        'original_filename': evidence.original_filename,
        'media_type': evidence.media_type,
        'file_size': evidence.file_size,
        'upload_timestamp': evidence.upload_timestamp.isoformat(),
        'processing_status': evidence.processing_status,
    }
