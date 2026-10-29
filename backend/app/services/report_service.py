import html
import json
import os
import uuid
from pathlib import Path

from app.models import AnalysisRun, Evidence, TimelineEvent, TranscriptSegment


def generate_pdf_report(output_path, title, evidence_items):
    """Create a record-derived PDF. Content is escaped before ReportLab parsing."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    except ImportError as error:
        _write_fallback_pdf(output_path, title, evidence_items)
        return os.fspath(output_path)

    styles = getSampleStyleSheet()
    font_name = 'Helvetica'
    font_bold = 'Helvetica-Bold'
    try:
        import reportlab
        vera = Path(reportlab.__file__).parent / 'fonts' / 'Vera.ttf'
        vera_bold = Path(reportlab.__file__).parent / 'fonts' / 'VeraBd.ttf'
        if vera.is_file() and vera_bold.is_file():
            pdfmetrics.registerFont(TTFont('CrimeVisionVera', str(vera)))
            pdfmetrics.registerFont(TTFont('CrimeVisionVera-Bold', str(vera_bold)))
            font_name, font_bold = 'CrimeVisionVera', 'CrimeVisionVera-Bold'
    except Exception:
        pass
    styles.add(ParagraphStyle(name='ReportTitle', parent=styles['Title'], fontName=font_bold, alignment=TA_CENTER, textColor=colors.HexColor('#0d1b2a')))
    styles.add(ParagraphStyle(name='ReportBody', parent=styles['BodyText'], fontName=font_name, leading=14, wordWrap='CJK'))
    styles.add(ParagraphStyle(name='ReportHeading', parent=styles['Heading2'], fontName=font_bold, textColor=colors.HexColor('#087e8b')))
    body = styles['ReportBody']
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=20*mm, bottomMargin=20*mm, title=title)
    story = [
        Paragraph(_safe(title), styles['ReportTitle']),
        Spacer(1, 6*mm),
        Paragraph('CrimeVision AI — Investigative decision-support report', body),
        Paragraph('Generated from records stored in this local application. Automated outputs are preliminary and require human review.', body),
        Spacer(1, 4*mm),
        Paragraph('Evidence inventory', styles['ReportHeading']),
    ]
    inventory = [[Paragraph('<b>Evidence ID</b>', body), Paragraph('<b>File</b>', body), Paragraph('<b>Type / Status</b>', body), Paragraph('<b>SHA-256</b>', body)]]
    for evidence in evidence_items:
        inventory.append([
            Paragraph(_safe(evidence.id), body), Paragraph(_safe(evidence.original_filename), body),
            Paragraph(_safe(f'{evidence.media_type} / {evidence.processing_status}'), body),
            Paragraph(_safe(evidence.file_hash), body),
        ])
    table = Table(inventory, colWidths=[34*mm, 43*mm, 35*mm, 60*mm], repeatRows=1, splitByRow=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dceef2')),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#9aa9b4')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend([table, Spacer(1, 5*mm)])

    for evidence in evidence_items:
        story.append(Paragraph(f'Evidence: {_safe(evidence.original_filename)} ({_safe(evidence.id)})', styles['ReportHeading']))
        story.append(Paragraph(f'Uploaded: {_safe(evidence.upload_timestamp.isoformat())} · Size: {evidence.file_size} bytes · Type: {_safe(evidence.media_type)}', body))
        analyses = AnalysisRun.query.filter_by(evidence_id=evidence.id).order_by(AnalysisRun.creation_timestamp.asc()).all()
        if not analyses:
            story.append(Paragraph('No analysis records are available for this evidence.', body))
        for analysis in analyses:
            story.append(Paragraph(f'Analysis { _safe(analysis.id) } — {_safe(analysis.analysis_type)} / {_safe(analysis.processing_status)}', body))
            story.append(Paragraph(f'Method/model: {_safe(analysis.model_identifier or "Not configured")} · Version: {_safe(analysis.model_version or "Not recorded")}', body))
            if analysis.error_details:
                story.append(Paragraph(f'Limitation: {_safe(_public_analysis_error(analysis))}', body))
            if analysis.result_metadata:
                metadata = json.loads(analysis.result_metadata)
                image_meta = metadata.get('image')
                if image_meta:
                    story.append(Paragraph(f'Image metadata: {_safe(str(image_meta))}', body))
                if metadata.get('limitations'):
                    for limitation in metadata['limitations']:
                        story.append(Paragraph(f'Limitation: {_safe(str(limitation))}', body))
            if analysis.detections:
                detection_rows = [['Class', 'Model score', 'Frame', 'Media time']]
                for detection in analysis.detections:
                    detection_rows.append([
                        _safe(detection.label), f'{detection.confidence:.4f}',
                        str(detection.frame_number) if detection.frame_number is not None else 'Image',
                        f'{detection.timestamp:.3f}s' if detection.timestamp is not None else '—',
                    ])
                detection_table = Table(detection_rows, repeatRows=1, hAlign='LEFT')
                detection_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf3f5')), ('GRID', (0, 0), (-1, -1), 0.3, colors.grey)]))
                story.extend([Spacer(1, 2*mm), detection_table])
            segments = TranscriptSegment.query.filter_by(analysis_run_id=analysis.id).order_by(TranscriptSegment.start_seconds.asc()).limit(50).all()
            if segments:
                story.append(Paragraph('Verbatim model transcription segments (unverified statements)', styles['ReportHeading']))
                for segment in segments:
                    story.append(Paragraph(f'{segment.start_seconds:.2f}s–{segment.end_seconds:.2f}s: {_safe(segment.text)}', body))
        events = TimelineEvent.query.filter_by(evidence_id=evidence.id).order_by(TimelineEvent.relative_seconds.asc()).limit(100).all()
        if events:
            story.append(Paragraph('Linked timeline entries', styles['ReportHeading']))
            for event in events:
                time_label = event.occurred_at.isoformat() if event.occurred_at else (
                    f'{event.relative_seconds:.2f}s ({event.time_basis})' if event.relative_seconds is not None else 'Time unknown'
                )
                story.append(Paragraph(f'{_safe(time_label)} · {_safe(event.source_type)} · {_safe(event.verification_status)}: {_safe(event.title)} — {_safe(event.description)}', body))
        story.append(Spacer(1, 5*mm))

    story.append(PageBreak())
    story.append(Paragraph('Methodology and limitations', styles['ReportHeading']))
    story.append(Paragraph('File hashes identify the exact uploaded bytes recorded by this application. They do not establish that a recording is authentic or complete.', body))
    story.append(Paragraph('Model detections and transcriptions may contain errors. A general object detector does not establish the presence or identity of a weapon, person, or criminal event unless its validated classes and operating conditions support that claim.', body))
    story.append(Paragraph('Video sample timestamps are media-relative and derived from decoded frame position and reported frame rate. They are not aligned to an external clock unless separately established.', body))
    story.append(Paragraph('Investigator review is required. This report is not a certification, official conclusion, or determination of guilt.', body))
    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return os.fspath(output_path)


def _safe(value):
    return html.escape(str(value), quote=True).replace('\n', '<br/>')


def _public_analysis_error(analysis):
    if analysis.processing_status in {'model_not_configured', 'model_unavailable'}:
        return 'The configured analysis model is unavailable; no model findings were generated.'
    return 'Analysis did not complete successfully.'


def _draw_footer(canvas, document):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColorRGB(0.35, 0.4, 0.45)
    canvas.drawString(document.leftMargin, 10*mm, 'CrimeVision AI · Preliminary analytical material · Human review required')
    canvas.drawRightString(A4[0] - document.rightMargin, 10*mm, f'Page {document.page}')
    canvas.restoreState()


def _write_fallback_pdf(output_path, title, evidence_items):
    """Write a conservative text PDF when optional ReportLab is unavailable."""
    import textwrap

    lines = [
        'CrimeVision AI - Investigative decision-support report',
        title,
        'PRELIMINARY ANALYTICAL MATERIAL - HUMAN REVIEW REQUIRED',
        '',
        'Evidence inventory',
    ]
    for evidence in evidence_items:
        lines.extend([
            f'Evidence ID: {evidence.id}',
            f'File: {evidence.original_filename}',
            f'Type/status: {evidence.media_type} / {evidence.processing_status}',
            f'SHA-256: {evidence.file_hash}',
            f'Upload record time: {evidence.upload_timestamp.isoformat()} · Size: {evidence.file_size} bytes',
        ])
        analyses = AnalysisRun.query.filter_by(evidence_id=evidence.id).order_by(AnalysisRun.creation_timestamp.asc()).all()
        for analysis in analyses:
            lines.extend(['', f'Analysis {analysis.id}: {analysis.analysis_type} / {analysis.processing_status}',
                          f'Model: {analysis.model_identifier or "Not configured"} / version {analysis.model_version or "not recorded"}'])
            if analysis.error_details:
                lines.append(f'Limitation: {_public_analysis_error(analysis)}')
            for detection in analysis.detections:
                lines.append(f'Detection from stored model output: {detection.label} · score {detection.confidence:.4f} · frame {detection.frame_number}')
            for segment in TranscriptSegment.query.filter_by(analysis_run_id=analysis.id).order_by(TranscriptSegment.start_seconds.asc()).limit(50):
                lines.append(f'Unverified transcript {segment.start_seconds:.2f}-{segment.end_seconds:.2f}s: {segment.text}')
        events = TimelineEvent.query.filter_by(evidence_id=evidence.id).order_by(TimelineEvent.created_at.asc()).limit(100).all()
        for event in events:
            time_label = event.occurred_at.isoformat() if event.occurred_at else (
                f'{event.relative_seconds:.2f}s ({event.time_basis})' if event.relative_seconds is not None else 'time unknown'
            )
            lines.append(f'Timeline {time_label} [{event.source_type}/{event.verification_status}]: {event.title} — {event.description}')

    lines.extend([
        '', 'Methodology and limitations',
        'File hashes identify the uploaded bytes recorded by this application. A hash does not establish authenticity or completeness.',
        'Model detections and transcriptions can be wrong. General object detection does not establish a weapon, identity, or criminal event.',
        'Video sampling timestamps are media-relative; no external clock synchronization is inferred.',
        'Investigator review is required. This report is not a certification, official conclusion, or determination of guilt.',
    ])
    wrapped = []
    for line in lines:
        wrapped.extend(textwrap.wrap(str(line), width=94, replace_whitespace=True, drop_whitespace=True) or [''])
    chunks = [wrapped[index:index + 50] for index in range(0, len(wrapped), 50)] or [[]]
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', None, b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    page_ids = []
    for page_number, chunk in enumerate(chunks, start=1):
        page_id = 4 + (page_number - 1) * 2
        stream_id = page_id + 1
        page_ids.append(page_id)
        commands = ['BT /F1 9 Tf 42 800 Td 12 TL']
        for line in chunk:
            safe_line = str(line).encode('cp1252', errors='replace').decode('cp1252')
            safe_line = safe_line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            commands.append(f'({safe_line}) Tj T*')
        commands.append(f'(Page {page_number} / {len(chunks)}) Tj ET')
        stream = '\n'.join(commands).encode('cp1252', errors='replace')
        objects.extend([
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>'.encode('ascii'),
            f'<< /Length {len(stream)} >>\nstream\n'.encode('ascii') + stream + b'\nendstream',
        ])
    objects[1] = f'<< /Type /Pages /Kids [{" ".join(f"{page_id} 0 R" for page_id in page_ids)}] /Count {len(page_ids)} >>'.encode('ascii')

    output = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for number, content in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f'{number} 0 obj\n'.encode('ascii'))
        output.extend(content)
        output.extend(b'\nendobj\n')
    xref_offset = len(output)
    output.extend(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
    output.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        output.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
    output.extend(f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n'.encode('ascii'))
    Path(output_path).write_bytes(output)
