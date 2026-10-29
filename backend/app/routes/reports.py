import json
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from app.extensions import db
from app.models import Evidence, ForensicReport
from app.services.report_service import generate_pdf_report

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('', methods=['POST'])
def create_report():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    evidence_ids = body.get('evidence_ids')
    if evidence_ids is not None and (not isinstance(evidence_ids, list) or len(evidence_ids) > 100):
        return jsonify({'error': 'evidence_ids must be a list of at most 100 identifiers.'}), 400
    if evidence_ids:
        evidence_items = Evidence.query.filter(Evidence.id.in_(evidence_ids)).all()
        if len(evidence_items) != len(set(evidence_ids)):
            return jsonify({'error': 'One or more evidence identifiers do not exist.'}), 404
    else:
        evidence_items = Evidence.query.order_by(Evidence.upload_timestamp.asc()).limit(100).all()
    if not evidence_items:
        return jsonify({'error': 'There are no evidence records to include in a report.'}), 400
    title = body.get('title', 'Forensic Evidence Report')
    if not isinstance(title, str) or not title.strip():
        return jsonify({'error': 'title must be a non-empty string.'}), 400

    report_id = str(uuid.uuid4())
    path = Path(current_app.config['REPORTS_FOLDER']) / f'{report_id}.pdf'
    try:
        generate_pdf_report(path, title.strip()[:255], evidence_items)
        if not path.is_file() or path.stat().st_size < 8:
            raise RuntimeError('Report generator returned no readable PDF.')
        report = ForensicReport(
            id=report_id, title=title.strip()[:255], status='completed',
            evidence_ids_json=json.dumps([item.id for item in evidence_items]), storage_path=str(path.resolve()),
        )
        db.session.add(report)
        db.session.commit()
    except RuntimeError as error:
        db.session.rollback()
        path.unlink(missing_ok=True)
        if str(error) == 'reportlab_not_installed':
            return jsonify({'error': 'PDF generation is unavailable. Install the backend ReportLab dependency.'}), 503
        current_app.logger.exception('Report generation failed')
        return jsonify({'error': 'Report generation failed.'}), 500
    except Exception:
        db.session.rollback()
        path.unlink(missing_ok=True)
        current_app.logger.exception('Report generation failed')
        return jsonify({'error': 'Report generation failed.'}), 500
    return jsonify({'report_id': report.id, 'title': report.title, 'status': report.status, 'created_at': report.created_at.isoformat(), 'download_url': f'/api/v1/reports/{report.id}/download'}), 201


@reports_bp.route('', methods=['GET'])
def list_reports():
    reports = ForensicReport.query.order_by(ForensicReport.created_at.desc()).limit(100).all()
    return jsonify({'reports': [{
        'report_id': item.id, 'title': item.title, 'status': item.status,
        'evidence_ids': json.loads(item.evidence_ids_json),
        'created_at': item.created_at.isoformat(),
        'download_url': f'/api/v1/reports/{item.id}/download',
    } for item in reports]})


@reports_bp.route('/<report_id>/download', methods=['GET'])
def download_report(report_id):
    report = ForensicReport.query.get_or_404(report_id)
    path = Path(report.storage_path).resolve()
    report_root = Path(current_app.config['REPORTS_FOLDER']).resolve()
    if path.parent != report_root or path.suffix.lower() != '.pdf' or not path.is_file():
        return jsonify({'error': 'Report file is unavailable.'}), 404
    return send_file(path, mimetype='application/pdf', as_attachment=True, download_name=f'crimevision-report-{report.id}.pdf')
