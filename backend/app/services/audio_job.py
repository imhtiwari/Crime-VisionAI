import json
import uuid
from datetime import datetime

from app.extensions import db
from app.models import AnalysisRun, Evidence, ProcessingJob, TimelineEvent, TranscriptSegment
from app.services.audio_service import audio_service


def process_audio_job(app, job_id):
    with app.app_context():
        job = db.session.get(ProcessingJob, job_id)
        if job is None or job.status != 'queued':
            return
        analysis = db.session.get(AnalysisRun, job.analysis_run_id)
        evidence = db.session.get(Evidence, job.evidence_id)
        job.status = 'running'
        job.started_at = datetime.utcnow()
        job.progress = 5
        if evidence and analysis:
            db.session.add(TimelineEvent(
                id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis.id,
                title='Audio transcription requested', description='An investigator requested speech transcription.',
                category='analysis_activity', source_type='analysis_execution',
                verification_status='unverified', time_basis='system_clock',
            ))
        db.session.commit()
        try:
            if analysis is None or evidence is None:
                raise ValueError('The linked evidence or analysis record is missing.')
            if audio_service.status != 'ready':
                analysis.processing_status = audio_service.status
                analysis.error_details = 'Transcription is unavailable. Install the optional Faster-Whisper dependencies and configure local model weights.'
                job.status = 'failed'
                job.message = analysis.error_details
                job.error_details = analysis.error_details
                job.completed_at = datetime.utcnow()
                analysis.completion_timestamp = datetime.utcnow()
                db.session.commit()
                return

            job.message = 'Transcribing audio with the configured local model.'
            db.session.commit()
            result = audio_service.transcribe(evidence.storage_path)
            for segment in result['segments']:
                db.session.add(TranscriptSegment(
                    id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis.id,
                    start_seconds=segment['start_seconds'], end_seconds=segment['end_seconds'],
                    text=segment['text'], language=result['language'],
                    language_probability=result['language_probability'],
                ))
                db.session.add(TimelineEvent(
                    id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis.id,
                    title='Transcribed speech segment', description=segment['text'],
                    category='transcript', source_type='verbatim_transcription',
                    verification_status='unverified', occurred_at=None,
                    relative_seconds=segment['start_seconds'], time_basis='media_relative',
                ))
            analysis.result_metadata = json.dumps({
                'language': result['language'],
                'language_probability': result['language_probability'],
                'duration_seconds': result['duration_seconds'],
                'segment_count': len(result['segments']),
            })
            analysis.model_identifier = audio_service.model_source
            analysis.processing_status = 'completed'
            analysis.completion_timestamp = datetime.utcnow()
            evidence.processing_status = 'transcribed'
            db.session.add(TimelineEvent(
                id=str(uuid.uuid4()), evidence_id=evidence.id, analysis_run_id=analysis.id,
                title='Audio transcription completed', description='Timestamped transcript segments were stored as unverified model output.',
                category='analysis_activity', source_type='analysis_execution',
                verification_status='unverified', time_basis='system_clock',
            ))
            job.status = 'completed'
            job.progress = 100
            job.message = 'Transcription completed. Transcript text is an unverified record of model output.'
            job.completed_at = datetime.utcnow()
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            job = db.session.get(ProcessingJob, job_id)
            analysis = db.session.get(AnalysisRun, job.analysis_run_id) if job else None
            if job:
                job.status = 'failed'
                job.error_details = 'Audio transcription failed. Check the model configuration and audio file.'
                job.message = 'Audio transcription failed.'
                job.completed_at = datetime.utcnow()
            if analysis:
                analysis.processing_status = 'failed'
                analysis.error_details = str(error)[:1000]
                analysis.completion_timestamp = datetime.utcnow()
            app.logger.exception('Audio transcription job failed')
            db.session.commit()
