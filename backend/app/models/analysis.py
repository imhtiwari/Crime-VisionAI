from datetime import datetime
from app.extensions import db

class AnalysisRun(db.Model):
    __tablename__ = "analysis_run"
    
    id = db.Column(db.String(36), primary_key=True)
    evidence_id = db.Column(db.String(36), db.ForeignKey("evidence.id"), nullable=False)
    analysis_type = db.Column(db.String(50), nullable=False)
    model_identifier = db.Column(db.String(255))
    model_version = db.Column(db.String(50))
    processing_status = db.Column(db.String(50), default="pending", nullable=False)
    creation_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completion_timestamp = db.Column(db.DateTime)
    result_metadata = db.Column(db.Text)
    error_details = db.Column(db.Text)
    
    detections = db.relationship("Detection", backref="analysis_run", lazy=True, cascade="all, delete-orphan")
    jobs = db.relationship("ProcessingJob", backref="analysis_run", lazy=True, cascade="all, delete-orphan")
    transcript_segments = db.relationship("TranscriptSegment", backref="analysis_run", lazy=True, cascade="all, delete-orphan")
    artifacts = db.relationship("AnalysisArtifact", backref="analysis_run", lazy=True, cascade="all, delete-orphan")
