from datetime import datetime

from app.extensions import db


class TimelineEvent(db.Model):
    __tablename__ = 'timeline_event'

    id = db.Column(db.String(36), primary_key=True)
    evidence_id = db.Column(db.String(36), db.ForeignKey('evidence.id'), index=True)
    analysis_run_id = db.Column(db.String(36), db.ForeignKey('analysis_run.id'), index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    source_type = db.Column(db.String(50), nullable=False)
    verification_status = db.Column(db.String(30), nullable=False, default='unverified')
    occurred_at = db.Column(db.DateTime, index=True)
    relative_seconds = db.Column(db.Float)
    time_basis = db.Column(db.String(40), nullable=False, default='unknown')
    confidence = db.Column(db.Float)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditEvent(db.Model):
    __tablename__ = 'audit_event'

    id = db.Column(db.String(36), primary_key=True)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(36), nullable=False, index=True)
    actor = db.Column(db.String(100), nullable=False, default='local_investigator')
    details_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
