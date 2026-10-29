from datetime import datetime

from app.extensions import db


class Conversation(db.Model):
    __tablename__ = 'conversation'

    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False, default='New investigation chat')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = db.relationship('ChatMessage', backref='conversation', lazy=True, cascade='all, delete-orphan')


class ChatMessage(db.Model):
    __tablename__ = 'chat_message'

    id = db.Column(db.String(36), primary_key=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversation.id'), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    structured_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
