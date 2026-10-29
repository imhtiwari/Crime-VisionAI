from datetime import datetime

from app.extensions import db


class TranscriptSegment(db.Model):
    __tablename__ = 'transcript_segment'

    id = db.Column(db.String(36), primary_key=True)
    evidence_id = db.Column(db.String(36), db.ForeignKey('evidence.id'), nullable=False, index=True)
    analysis_run_id = db.Column(db.String(36), db.ForeignKey('analysis_run.id'), nullable=False, index=True)
    start_seconds = db.Column(db.Float, nullable=False)
    end_seconds = db.Column(db.Float, nullable=False)
    text = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(30))
    language_probability = db.Column(db.Float)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
