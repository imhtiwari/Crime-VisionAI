import os
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from app.config import settings
from app.extensions import db
from app.routes.analysis import analysis_bp
from app.routes.evidence import evidence_bp
from app.routes.health import health_bp
from app.routes.jobs import jobs_bp
from app.routes.timeline import timeline_bp
from app.routes.chat import chat_bp
from app.routes.reports import reports_bp
from app.routes.dashboard import dashboard_bp


def create_app(test_config=None):
    """Create the Flask application and initialize its database and storage."""
    app = Flask(__name__)
    backend_root = Path(__file__).resolve().parent.parent
    app.config.update(
        SECRET_KEY=settings.SECRET_KEY,
        SQLALCHEMY_DATABASE_URI=settings.DATABASE_URL,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=settings.MAX_UPLOAD_SIZE,
        UPLOAD_FOLDER=_resolve_path(backend_root, settings.UPLOAD_FOLDER),
        EVIDENCE_FOLDER=_resolve_path(backend_root, settings.EVIDENCE_FOLDER),
        REPORTS_FOLDER=_resolve_path(backend_root, settings.REPORTS_FOLDER),
        THUMBNAILS_FOLDER=_resolve_path(backend_root, settings.THUMBNAILS_FOLDER),
        DERIVED_FOLDER=_resolve_path(backend_root, settings.DERIVED_FOLDER),
        MAX_VIDEO_DURATION=settings.MAX_VIDEO_DURATION,
        VIDEO_FRAME_SAMPLE_INTERVAL=settings.VIDEO_FRAME_SAMPLE_INTERVAL,
        MAX_VIDEO_FRAMES=settings.MAX_VIDEO_FRAMES,
        MAX_CONCURRENT_JOBS=settings.MAX_CONCURRENT_JOBS,
        DETECTION_CONFIDENCE_THRESHOLD=settings.DETECTION_CONFIDENCE_THRESHOLD,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(',') if origin.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins}})
    app.register_blueprint(health_bp, url_prefix='/api/v1')
    app.register_blueprint(evidence_bp, url_prefix='/api/v1/evidence')
    app.register_blueprint(analysis_bp, url_prefix='/api/v1/analysis')
    app.register_blueprint(jobs_bp, url_prefix='/api/v1/jobs')
    app.register_blueprint(timeline_bp, url_prefix='/api/v1/timeline')
    app.register_blueprint(chat_bp, url_prefix='/api/v1/chat')
    app.register_blueprint(reports_bp, url_prefix='/api/v1/reports')
    app.register_blueprint(dashboard_bp, url_prefix='/api/v1/dashboard')

    @app.errorhandler(RequestEntityTooLarge)
    def handle_upload_too_large(_error):
        return jsonify({'error': 'File exceeds the configured upload size limit.'}), 413

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({'error': error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception('Unhandled API error')
        return jsonify({'error': 'An unexpected server error occurred.'}), 500

    for key in ('UPLOAD_FOLDER', 'EVIDENCE_FOLDER', 'REPORTS_FOLDER', 'THUMBNAILS_FOLDER', 'DERIVED_FOLDER'):
        os.makedirs(app.config[key], exist_ok=True)

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()
        _mark_interrupted_jobs_failed()

    return app


def _resolve_path(root, configured_path):
    path = Path(configured_path)
    return str(path if path.is_absolute() else root / path)


def _mark_interrupted_jobs_failed():
    from datetime import datetime
    from app.models import ProcessingJob

    interrupted = ProcessingJob.query.filter(ProcessingJob.status.in_(['queued', 'running'])).all()
    for job in interrupted:
        job.status = 'failed'
        job.error_details = 'The application restarted before this job completed.'
        job.message = 'Interrupted by application restart.'
        job.completed_at = datetime.utcnow()
    if interrupted:
        db.session.commit()
