import json
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import AnalysisRun, AuditEvent, Evidence, TimelineEvent

timeline_bp = Blueprint('timeline', __name__)


@timeline_bp.route('', methods=['GET'], strict_slashes=False)
def get_timeline():
    query = TimelineEvent.query
    evidence_id = request.args.get('evidence_id')
    source_type = request.args.get('source_type')
    category = request.args.get('category')
    after = request.args.get('after')
    before = request.args.get('before')
    if evidence_id:
        query = query.filter_by(evidence_id=evidence_id)
    if source_type:
        query = query.filter_by(source_type=source_type)
    if category:
        query = query.filter_by(category=category)
    try:
        if after:
            query = query.filter(TimelineEvent.occurred_at >= _parse_datetime(after))
        if before:
            query = query.filter(TimelineEvent.occurred_at <= _parse_datetime(before))
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    events = query.order_by(TimelineEvent.occurred_at.asc().nullslast(), TimelineEvent.relative_seconds.asc().nullslast(), TimelineEvent.created_at.asc()).limit(500).all()
    return jsonify({'events': [_serialize_event(event) for event in events]})


@timeline_bp.route('/events', methods=['POST'])
def create_timeline_event():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    title = _text(body.get('title'), 255)
    description = _text(body.get('description'), 5000)
    category = _text(body.get('category'), 50)
    if not title or not description or not category:
        return jsonify({'error': 'title, description, and category are required.'}), 400

    evidence_id = body.get('evidence_id')
    analysis_id = body.get('analysis_id')
    if evidence_id and Evidence.query.get(evidence_id) is None:
        return jsonify({'error': 'evidence_id does not identify an existing evidence item.'}), 404
    if analysis_id:
        analysis = AnalysisRun.query.get(analysis_id)
        if analysis is None or (evidence_id and analysis.evidence_id != evidence_id):
            return jsonify({'error': 'analysis_id does not match the selected evidence.'}), 400
        evidence_id = evidence_id or analysis.evidence_id

    try:
        occurred_at = _parse_datetime(body['occurred_at']) if body.get('occurred_at') else None
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    relative_seconds = body.get('relative_seconds')
    if relative_seconds is not None and (not isinstance(relative_seconds, (int, float)) or relative_seconds < 0):
        return jsonify({'error': 'relative_seconds must be a non-negative number.'}), 400
    time_basis = body.get('time_basis', 'investigator_supplied' if occurred_at else 'unknown')
    event = TimelineEvent(
        id=str(uuid.uuid4()), evidence_id=evidence_id, analysis_run_id=analysis_id,
        title=title, description=description, category=category,
        source_type='investigator_annotation', verification_status='unverified',
        occurred_at=occurred_at, relative_seconds=relative_seconds,
        time_basis=time_basis,
    )
    db.session.add(event)
    db.session.add(AuditEvent(
        id=str(uuid.uuid4()), action='timeline.created', entity_type='timeline_event',
        entity_id=event.id, details_json=json.dumps({'source_type': event.source_type}),
    ))
    db.session.commit()
    return jsonify(_serialize_event(event)), 201


@timeline_bp.route('/events/<event_id>', methods=['PATCH'])
def update_timeline_event(event_id):
    event = TimelineEvent.query.get_or_404(event_id)
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not body:
        return jsonify({'error': 'A non-empty JSON object is required.'}), 400
    before = _serialize_event(event)
    allowed = {'title', 'description', 'category', 'verification_status', 'occurred_at', 'relative_seconds'}
    if set(body) - allowed:
        return jsonify({'error': 'The request contains fields that cannot be changed.'}), 400
    for key, limit in (('title', 255), ('description', 5000), ('category', 50)):
        if key in body:
            value = _text(body[key], limit)
            if not value:
                return jsonify({'error': f'{key} cannot be empty.'}), 400
            setattr(event, key, value)
    if 'verification_status' in body:
        if body['verification_status'] not in {'unverified', 'review_required', 'verified'}:
            return jsonify({'error': 'verification_status is invalid.'}), 400
        event.verification_status = body['verification_status']
    if 'occurred_at' in body:
        try:
            event.occurred_at = _parse_datetime(body['occurred_at']) if body['occurred_at'] else None
        except ValueError as error:
            return jsonify({'error': str(error)}), 400
    if 'relative_seconds' in body:
        value = body['relative_seconds']
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            return jsonify({'error': 'relative_seconds must be a non-negative number.'}), 400
        event.relative_seconds = value
    event.updated_at = datetime.utcnow()
    db.session.add(AuditEvent(
        id=str(uuid.uuid4()), action='timeline.updated', entity_type='timeline_event',
        entity_id=event.id, details_json=json.dumps({'before': before, 'changes': body}),
    ))
    db.session.commit()
    return jsonify(_serialize_event(event))


def _parse_datetime(value):
    if not isinstance(value, str):
        raise ValueError('Datetime values must be ISO 8601 strings.')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('Datetime values must be valid ISO 8601.') from error


def _text(value, limit):
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value[:limit] if value else None


def _serialize_event(event):
    return {
        'event_id': event.id,
        'evidence_id': event.evidence_id,
        'analysis_id': event.analysis_run_id,
        'title': event.title,
        'description': event.description,
        'category': event.category,
        'source_type': event.source_type,
        'verification_status': event.verification_status,
        'occurred_at': event.occurred_at.isoformat() if event.occurred_at else None,
        'relative_seconds': event.relative_seconds,
        'time_basis': event.time_basis,
        'confidence': event.confidence,
        'metadata': json.loads(event.metadata_json) if event.metadata_json else None,
        'created_at': event.created_at.isoformat(),
        'updated_at': event.updated_at.isoformat(),
    }
