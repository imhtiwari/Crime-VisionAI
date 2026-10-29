from concurrent.futures import ThreadPoolExecutor

from app.config import settings
from app.extensions import db
from app.models import ProcessingJob
from app.services.audio_job import process_audio_job
from app.services.video_service import process_video_job


_executor = ThreadPoolExecutor(max_workers=max(1, settings.MAX_CONCURRENT_JOBS), thread_name_prefix='crimevision-job')


def submit_job(app, job_id):
    with app.app_context():
        job = db.session.get(ProcessingJob, job_id)
        if job is None:
            raise LookupError('Processing job does not exist.')
        queued = ProcessingJob.query.filter_by(status='queued').count()
        running = ProcessingJob.query.filter_by(status='running').count()
        if queued + running > settings.MAX_CONCURRENT_JOBS:
            raise RuntimeError('Processing queue is full.')
        job_type = job.job_type
    processor = process_video_job if job_type == 'video' else process_audio_job
    _executor.submit(processor, app, job_id)
