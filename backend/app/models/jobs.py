from datetime import datetime

from app.extensions import db


class ProcessingJob(db.Model):
    __tablename__ = 'processing_job'

    id = db.Column(db.String(36), primary_key=True)
    evidence_id = db.Column(db.String(36), db.ForeignKey('evidence.id'), nullable=False, index=True)
    analysis_run_id = db.Column(db.String(36), db.ForeignKey('analysis_run.id'), nullable=False, index=True)
    job_type = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='queued', index=True)
    progress = db.Column(db.Integer, nullable=False, default=0)
    message = db.Column(db.String(500))
    error_details = db.Column(db.Text)
    options_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
