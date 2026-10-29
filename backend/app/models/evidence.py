from datetime import datetime
from app.extensions import db

class Evidence(db.Model):
    __tablename__ = "evidence"
    
    id = db.Column(db.String(36), primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    internal_filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(512), nullable=False)
    media_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    file_hash = db.Column(db.String(64), nullable=False, unique=True)
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processing_status = db.Column(db.String(50), default="pending", nullable=False)

    analyses = db.relationship("AnalysisRun", backref="evidence", lazy=True, cascade="all, delete-orphan")
    jobs = db.relationship("ProcessingJob", backref="evidence", lazy=True, cascade="all, delete-orphan")
    timeline_events = db.relationship("TimelineEvent", backref="evidence", lazy=True)
