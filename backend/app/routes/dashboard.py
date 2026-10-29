from collections import Counter
from datetime import datetime, timedelta

from flask import Blueprint, jsonify
from sqlalchemy import func

from app.models import AnalysisRun, Evidence, ForensicReport, ProcessingJob, TimelineEvent
from app.routes.jobs import _serialize_job

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('', methods=['GET'], strict_slashes=False)
def dashboard_data():
    evidence_total = Evidence.query.count()
    evidence_groups = {}
    for media_type, count in Evidence.query.with_entities(Evidence.media_type, func.count(Evidence.id)).group_by(Evidence.media_type).all():
        evidence_groups[media_type] = count

    analyses = AnalysisRun.query.order_by(AnalysisRun.creation_timestamp.desc()).limit(8).all()
    jobs = ProcessingJob.query.order_by(ProcessingJob.created_at.desc()).limit(8).all()
    recent_evidence = Evidence.query.order_by(Evidence.upload_timestamp.desc()).limit(8).all()
    cutoff = datetime.utcnow() - timedelta(days=6)
    event_times = TimelineEvent.query.filter(TimelineEvent.created_at >= cutoff).with_entities(TimelineEvent.created_at).all()
    daily = Counter(event.date().isoformat() for (event,) in event_times)
    activity = []
    for offset in range(7):
        day = (cutoff.date() + timedelta(days=offset)).isoformat()
        activity.append({'date': day, 'events': daily.get(day, 0)})

    return jsonify({
        'statistics': {
            'total_evidence': evidence_total,
            'evidence_by_type': evidence_groups,
            'images_analyzed': AnalysisRun.query.filter_by(analysis_type='image_detection').filter(AnalysisRun.processing_status.in_(['completed', 'model_not_configured', 'model_unavailable', 'completed_metadata_only'])).count(),
            'videos_processed': AnalysisRun.query.filter_by(analysis_type='video_frame_analysis').filter(AnalysisRun.processing_status.in_(['completed', 'completed_metadata_only'])).count(),
            'audio_transcribed': AnalysisRun.query.filter_by(analysis_type='audio_transcription', processing_status='completed').count(),
            'reports_generated': ForensicReport.query.count(),
            'pending_jobs': ProcessingJob.query.filter(ProcessingJob.status.in_(['queued', 'running'])).count(),
        },
        'recent_evidence': [{
            'id': item.id, 'original_filename': item.original_filename, 'media_type': item.media_type,
            'processing_status': item.processing_status, 'upload_timestamp': item.upload_timestamp.isoformat(),
        } for item in recent_evidence],
        'recent_analyses': [{
            'analysis_id': item.id, 'evidence_id': item.evidence_id, 'analysis_type': item.analysis_type,
            'processing_status': item.processing_status,
            'creation_timestamp': item.creation_timestamp.isoformat(),
            'completion_timestamp': item.completion_timestamp.isoformat() if item.completion_timestamp else None,
        } for item in analyses],
        'recent_jobs': [_serialize_job(job) for job in jobs],
        'timeline_activity': activity,
    })
