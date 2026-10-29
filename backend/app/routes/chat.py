import json
import uuid
from datetime import datetime

import requests
from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import AnalysisRun, ChatMessage, Conversation, Evidence, TranscriptSegment
from app.services.llm_service import llm_service

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/conversations', methods=['POST'])
def create_conversation():
    body = request.get_json(silent=True) or {}
    title = body.get('title', 'New investigation chat')
    if not isinstance(title, str) or not title.strip():
        return jsonify({'error': 'title must be a non-empty string.'}), 400
    conversation = Conversation(id=str(uuid.uuid4()), title=title.strip()[:255])
    db.session.add(conversation)
    db.session.commit()
    return jsonify({'conversation_id': conversation.id, 'title': conversation.title, 'created_at': conversation.created_at.isoformat()}), 201


@chat_bp.route('/conversations', methods=['GET'])
def list_conversations():
    conversations = Conversation.query.order_by(Conversation.updated_at.desc()).limit(100).all()
    return jsonify({'conversations': [{
        'conversation_id': item.id, 'title': item.title,
        'created_at': item.created_at.isoformat(), 'updated_at': item.updated_at.isoformat(),
        'message_count': len(item.messages),
    } for item in conversations]})


@chat_bp.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    messages = ChatMessage.query.filter_by(conversation_id=conversation.id).order_by(ChatMessage.created_at.asc()).all()
    return jsonify({
        'conversation_id': conversation.id,
        'title': conversation.title,
        'messages': [{
            'message_id': item.id, 'role': item.role, 'content': item.content,
            'structured': json.loads(item.structured_json) if item.structured_json else None,
            'created_at': item.created_at.isoformat(),
        } for item in messages],
    })


@chat_bp.route('/conversations/<conversation_id>/messages', methods=['POST'])
def send_message(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    question = body.get('message')
    if not isinstance(question, str) or not question.strip() or len(question) > 8000:
        return jsonify({'error': 'message must contain between 1 and 8000 characters.'}), 400
    evidence_ids = body.get('evidence_ids')
    if evidence_ids is not None and (not isinstance(evidence_ids, list) or len(evidence_ids) > 50):
        return jsonify({'error': 'evidence_ids must be a list of at most 50 identifiers.'}), 400
    evidence_query = Evidence.query.order_by(Evidence.upload_timestamp.desc())
    if evidence_ids:
        evidence_query = evidence_query.filter(Evidence.id.in_(evidence_ids))
    records = evidence_query.limit(20).all()
    if evidence_ids and len(records) != len(set(evidence_ids)):
        return jsonify({'error': 'One or more selected evidence identifiers do not exist.'}), 404
    context = [_evidence_context(item) for item in records]

    user_message = ChatMessage(id=str(uuid.uuid4()), conversation_id=conversation.id, role='user', content=question.strip())
    db.session.add(user_message)
    db.session.commit()
    history_rows = ChatMessage.query.filter_by(conversation_id=conversation.id).order_by(ChatMessage.created_at.desc()).limit(12).all()
    history = [{'role': item.role, 'content': item.content[:4000]} for item in reversed(history_rows) if item.role in {'user', 'assistant'}]
    if history and history[-1]['role'] == 'user':
        history.pop()
    try:
        structured = llm_service.answer(question.strip(), history, context)
    except RuntimeError as error:
        return jsonify({'error': 'The investigation assistant is not configured or is rate limited.', 'provider_status': str(error)}), 503
    except requests.RequestException:
        return jsonify({'error': 'The configured investigation provider is currently unavailable.'}), 503
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return jsonify({'error': 'The investigation provider returned an invalid response.'}), 502

    assistant = ChatMessage(
        id=str(uuid.uuid4()), conversation_id=conversation.id, role='assistant',
        content=structured['answer'], structured_json=json.dumps(structured, ensure_ascii=False),
    )
    conversation.updated_at = datetime.utcnow()
    db.session.add(assistant)
    db.session.commit()
    return jsonify({'message_id': assistant.id, 'role': 'assistant', 'structured': structured}), 200


def _evidence_context(evidence):
    analyses = AnalysisRun.query.filter_by(evidence_id=evidence.id).order_by(AnalysisRun.creation_timestamp.desc()).limit(10).all()
    return {
        'evidence_id': evidence.id,
        'filename': evidence.original_filename,
        'media_type': evidence.media_type,
        'file_size': evidence.file_size,
        'sha256': evidence.file_hash,
        'uploaded_at': evidence.upload_timestamp.isoformat(),
        'analyses': [{
            'analysis_id': analysis.id,
            'type': analysis.analysis_type,
            'status': analysis.processing_status,
            'result_metadata': json.loads(analysis.result_metadata) if analysis.result_metadata else None,
            'detections': [{
                'label': detection.label, 'confidence': detection.confidence,
                'frame_number': detection.frame_number, 'timestamp': detection.timestamp,
            } for detection in analysis.detections],
            'transcript_segments': [{
                'start_seconds': segment.start_seconds, 'end_seconds': segment.end_seconds,
                'text': segment.text,
            } for segment in TranscriptSegment.query.filter_by(analysis_run_id=analysis.id).limit(100).all()],
        } for analysis in analyses],
    }
