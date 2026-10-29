from datetime import datetime
from app.extensions import db

class Detection(db.Model):
    __tablename__ = "detection"
    
    id = db.Column(db.String(36), primary_key=True)
    analysis_run_id = db.Column(db.String(36), db.ForeignKey("analysis_run.id"), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    bbox_x1 = db.Column(db.Float, nullable=False)
    bbox_y1 = db.Column(db.Float, nullable=False)
    bbox_x2 = db.Column(db.Float, nullable=False)
    bbox_y2 = db.Column(db.Float, nullable=False)
    frame_number = db.Column(db.Integer)
    timestamp = db.Column(db.Float)
