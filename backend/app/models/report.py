from datetime import datetime

from app.extensions import db


class ForensicReport(db.Model):
    __tablename__ = 'forensic_report'

    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='completed')
    evidence_ids_json = db.Column(db.Text, nullable=False)
    storage_path = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
