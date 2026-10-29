from datetime import datetime

from app.extensions import db


class AnalysisArtifact(db.Model):
    __tablename__ = 'analysis_artifact'

    id = db.Column(db.String(36), primary_key=True)
    analysis_run_id = db.Column(db.String(36), db.ForeignKey('analysis_run.id'), nullable=False, index=True)
    kind = db.Column(db.String(50), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    storage_path = db.Column(db.String(512), nullable=False)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
