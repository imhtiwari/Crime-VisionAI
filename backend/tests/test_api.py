import hashlib
import io
import json
import time
import shutil
import uuid
import unittest
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app import create_app
from app.extensions import db
from app.models import AuditEvent, Evidence, ProcessingJob
from app.services.llm_service import validate_response


class CrimeVisionApiTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).parent / '.test-run'
        test_root.mkdir(exist_ok=True)
        root = test_root / str(uuid.uuid4())
        root.mkdir()
        self.temp = root
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'UPLOAD_FOLDER': str(root / 'uploads'),
            'EVIDENCE_FOLDER': str(root / 'evidence'),
            'REPORTS_FOLDER': str(root / 'reports'),
            'THUMBNAILS_FOLDER': str(root / 'thumbnails'),
            'DERIVED_FOLDER': str(root / 'derived'),
            'MAX_CONTENT_LENGTH': 1024 * 1024,
            'MAX_VIDEO_DURATION': 30,
            'MAX_VIDEO_FRAMES': 20,
            'VIDEO_FRAME_SAMPLE_INTERVAL': 1,
            'MAX_CONCURRENT_JOBS': 2,
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        shutil.rmtree(self.temp, ignore_errors=True)

    @staticmethod
    def image_bytes():
        image = Image.new('RGB', (32, 24), color=(30, 120, 210))
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()

    def upload(self, data=None, filename='evidence.png'):
        return self.client.post('/api/v1/evidence/upload', data={
            'file': (io.BytesIO(data if data is not None else self.image_bytes()), filename),
        }, content_type='multipart/form-data')

    def test_health_capabilities_and_empty_dashboard(self):
        self.assertEqual(self.client.get('/api/v1/health').status_code, 200)
        capabilities = self.client.get('/api/v1/capabilities').get_json()
        self.assertNotIn('GROQ_API_KEY', json.dumps(capabilities))
        dashboard = self.client.get('/api/v1/dashboard').get_json()
        self.assertEqual(dashboard['statistics']['total_evidence'], 0)
        self.assertEqual(dashboard['recent_jobs'], [])

    def test_upload_hash_persistence_duplicate_download_and_analysis(self):
        raw = self.image_bytes()
        response = self.upload(raw)
        self.assertEqual(response.status_code, 201)
        record = response.get_json()
        self.assertEqual(record['file_hash'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.client.get(f"/api/v1/evidence/{record['evidence_id']}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/evidence/{record['evidence_id']}/download").data, raw)
        self.assertEqual(self.upload(raw).status_code, 409)
        analysis = self.client.post(f"/api/v1/analysis/image/{record['evidence_id']}", json={}).get_json()
        self.assertIn(analysis['status'], {'completed', 'model_unavailable', 'model_not_configured'})
        self.assertEqual(analysis['detector']['detections'], [])
        details = self.client.get(f"/api/v1/analysis/{analysis['analysis_id']}").get_json()
        self.assertEqual(details['findings'], [])

    def test_invalid_uploads_are_rejected_without_records(self):
        self.assertEqual(self.upload(b'not an image').status_code, 400)
        self.assertEqual(self.upload(self.image_bytes(), '../unsafe.png').status_code, 201)
        self.assertEqual(self.upload(self.image_bytes(), 'unsupported.exe').status_code, 400)
        listing = self.client.get('/api/v1/evidence').get_json()
        self.assertEqual(listing['total'], 1)

    def test_investigator_timeline_and_audit_history(self):
        created = self.client.post('/api/v1/timeline/events', json={
            'title': 'Review note', 'description': 'Time not independently established.',
            'category': 'investigator_note', 'relative_seconds': 4.5,
            'time_basis': 'investigator_supplied_media_relative',
        })
        self.assertEqual(created.status_code, 201)
        event_id = created.get_json()['event_id']
        updated = self.client.patch(f'/api/v1/timeline/events/{event_id}', json={'verification_status': 'verified'})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()['verification_status'], 'verified')
        with self.app.app_context():
            self.assertEqual(AuditEvent.query.count(), 2)

    def test_chat_schema_discards_unmatched_citations(self):
        answer = validate_response({
            'answer': 'Only one source matched.', 'observations': [], 'interpretations': [],
            'hypotheses': [], 'uncertainties': [], 'citations': [
                {'evidence_id': 'valid', 'analysis_id': None, 'reference': 'record'},
                {'evidence_id': 'made-up', 'analysis_id': None, 'reference': 'invented'},
            ],
        }, [{'evidence_id': 'valid', 'analyses': []}])
        self.assertEqual(len(answer['citations']), 1)
        self.assertIn('omitted', answer['uncertainties'][0])

    def test_report_endpoint_returns_a_valid_pdf(self):
        upload = self.upload().get_json()
        response = self.client.post('/api/v1/reports', json={'evidence_ids': [upload['evidence_id']]})
        self.assertEqual(response.status_code, 201)
        download = self.client.get(response.get_json()['download_url'])
        self.assertEqual(download.status_code, 200)
        self.assertTrue(download.data.startswith(b'%PDF-'))
        self.assertTrue(download.data.rstrip().endswith(b'%%EOF'))

    def test_wav_evidence_and_transcription_graceful_when_optional_model_missing(self):
        wav_data = io.BytesIO()
        with wave.open(wav_data, 'wb') as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(16000)
            writer.writeframes(b'\x00\x00' * 1600)
        uploaded = self.client.post('/api/v1/evidence/upload', data={
            'file': (io.BytesIO(wav_data.getvalue()), 'statement.wav'),
        }, content_type='multipart/form-data')
        self.assertEqual(uploaded.status_code, 201, uploaded.get_data(as_text=True))
        evidence_id = uploaded.get_json()['evidence_id']
        started = self.client.post(f'/api/v1/analysis/audio/{evidence_id}')
        self.assertEqual(started.status_code, 202, started.get_data(as_text=True))
        job_id = started.get_json()['job_id']
        for _ in range(50):
            job_response = self.client.get(f'/api/v1/jobs/{job_id}')
            if job_response.get_json()['status'] in {'completed', 'failed'}:
                break
            time.sleep(0.05)
        transcript = self.client.get(f'/api/v1/analysis/audio/{evidence_id}/transcript')
        self.assertEqual(transcript.status_code, 200)
        if transcript.get_json()['status'] != 'completed':
            self.assertEqual(transcript.get_json()['segments'], [])

    def test_video_frame_sampling_job_or_corrupt_container_validation(self):
        path = self.temp / 'sample.avi'
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 5, (64, 48))
        if not writer.isOpened():
            self.skipTest('OpenCV MJPG VideoWriter is unavailable on this host.')
        for index in range(5):
            writer.write(np.full((48, 64, 3), index * 20, dtype=np.uint8))
        writer.release()
        with path.open('rb') as video_file:
            uploaded = self.client.post('/api/v1/evidence/upload', data={'file': (video_file, 'sample.avi')}, content_type='multipart/form-data')
        self.assertEqual(uploaded.status_code, 201, uploaded.get_data(as_text=True))
        evidence_id = uploaded.get_json()['evidence_id']
        response = self.client.post(f'/api/v1/analysis/video/{evidence_id}', json={'sampling_interval_seconds': 1})
        self.assertEqual(response.status_code, 202, response.get_data(as_text=True))
        job_id = response.get_json()['job_id']
        for _ in range(50):
            job_response = self.client.get(f'/api/v1/jobs/{job_id}')
            status = job_response.get_json()['status']
            if status in {'completed', 'failed'}:
                break
            time.sleep(0.05)
        self.assertEqual(status, 'completed', job_response.get_data(as_text=True))
        self.assertGreaterEqual(job_response.get_json()['progress'], 100)


if __name__ == '__main__':
    unittest.main()
