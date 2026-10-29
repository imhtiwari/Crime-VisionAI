from flask import Blueprint, jsonify, request

from app.models import ProcessingJob

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('', methods=['GET'])
def list_jobs():
    limit = request.args.get('limit', 20, type=int)
    if limit < 1 or limit > 100:
        return jsonify({'error': 'limit must be between 1 and 100.'}), 400
    query = ProcessingJob.query
    evidence_id = request.args.get('evidence_id')
    status = request.args.get('status')
    if evidence_id:
        query = query.filter_by(evidence_id=evidence_id)
    if status:
        if status not in {'queued', 'running', 'completed', 'failed', 'cancelled'}:
            return jsonify({'error': 'status is invalid.'}), 400
        query = query.filter_by(status=status)
    jobs = query.order_by(ProcessingJob.created_at.desc()).limit(limit).all()
    return jsonify({'jobs': [_serialize_job(job) for job in jobs]})


@jobs_bp.route('/<job_id>', methods=['GET'])
def get_job(job_id):
    job = ProcessingJob.query.get_or_404(job_id)
    return jsonify(_serialize_job(job))


def _serialize_job(job):
    return {
        'job_id': job.id,
        'evidence_id': job.evidence_id,
        'analysis_id': job.analysis_run_id,
        'job_type': job.job_type,
        'status': job.status,
        'progress': job.progress,
        'message': job.message,
        'error': 'Processing failed. Check service configuration and server logs.' if job.status == 'failed' else None,
        'created_at': job.created_at.isoformat(),
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
    }
