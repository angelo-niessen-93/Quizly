"""External integrations are mocked; no credentials or network are required."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from . import ai
from .ai_schema import generation_config, validate_generated_content
from .models import Quiz
from .tests import URL, quiz_content
from .validators import validate_youtube_url

UNSAFE_URLS = [
    'http://youtube.com/watch?v=dQw4w9WgXcQ',
    'https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ',
    'https://evil.com/',
    'file:///etc/passwd',
    'garbage',
    'https://user@youtube.com/watch?v=dQw4w9WgXcQ',
    'https://youtube.com:443/watch?v=dQw4w9WgXcQ',
    'https://youtube.com/watch?v=short',
    'https://youtube.com/playlist?list=test',
]


class YouTubeURLTests(SimpleTestCase):
    def test_allowed_urls_are_canonicalized(self):
        """Short, mobile, embedded and shorts links map to one video URL."""
        for url in [
            URL,
            'https://youtu.be/dQw4w9WgXcQ?t=3',
            'https://m.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtube.com/shorts/dQw4w9WgXcQ',
            'https://www.youtube.com/embed/dQw4w9WgXcQ',
        ]:
            self.assertEqual(validate_youtube_url(url), URL)

    def test_unsafe_urls_are_rejected(self):
        """Reject arbitrary hosts, malformed IDs, userinfo and ports."""
        for url in UNSAFE_URLS:
            with self.subTest(url=url), self.assertRaises(ValidationError):
                validate_youtube_url(url)


class AIServiceTests(SimpleTestCase):
    @override_settings(OPENAI_API_KEY='', GEMINI_API_KEY='')
    def test_missing_keys_prevent_download(self):
        """No external processing starts without configured credentials."""
        with patch.object(ai, 'download_audio') as download:
            with self.assertRaises(ai.GenerationUnavailable):
                ai.generate_content(URL)
        download.assert_not_called()

    @override_settings(OPENAI_API_KEY='test', GEMINI_API_KEY='test')
    def test_missing_ffmpeg_is_reported(self):
        """Absent audio tools produce a safe configuration error."""
        with patch.object(ai, 'which', return_value=None):
            with self.assertRaises(ai.GenerationUnavailable):
                ai.require_configuration()

    def test_video_metadata_limits(self):
        """Live, unknown-duration and oversized videos are rejected."""
        for info in [
            {'is_live': True, 'duration': 60},
            {},
            {'duration': 1201},
            {'duration': 0},
        ]:
            with self.assertRaises(ValidationError):
                ai.validate_video(info)
        ai.validate_video({'duration': 1200, 'is_live': False})

    def fake_download(self, url, directory):
        """Create a temporary placeholder to inspect subsequent cleanup."""
        self.audio = Path(directory) / 'audio.mp3'
        self.audio.write_bytes(b'test audio')
        return self.audio

    def test_success_removes_temporary_files(self):
        """The pipeline cleans its files after successful generation."""
        with (
            patch.object(ai, 'require_configuration'),
            patch.object(ai, 'download_audio', side_effect=self.fake_download),
            patch.object(ai, 'transcribe_audio', return_value='Transcript'),
            patch.object(
                ai, 'generate_questions', return_value=quiz_content()
            ),
        ):
            result = ai.generate_content(URL)
        self.assertEqual(result, quiz_content())
        self.assertFalse(self.audio.parent.exists())

    def test_failure_removes_temporary_files(self):
        """Whisper failures also clean the entire temporary directory."""
        with (
            patch.object(ai, 'require_configuration'),
            patch.object(ai, 'download_audio', side_effect=self.fake_download),
            patch.object(
                ai,
                'transcribe_audio',
                side_effect=ValueError('private details'),
            ),
        ):
            with self.assertRaises(ai.GenerationFailed):
                ai.generate_content(URL)
        self.assertFalse(self.audio.parent.exists())

    def failing_download(self, url, directory):
        """Simulate a failed download that already wrote partial data."""
        self.fake_download(url, directory)
        raise ai.DownloadError('private provider details')

    def test_partial_download_is_removed(self):
        """Download failures cannot leave audio fragments on disk."""
        with (
            patch.object(ai, 'require_configuration'),
            patch.object(
                ai, 'download_audio', side_effect=self.failing_download
            ),
        ):
            with self.assertRaises(ai.GenerationFailed):
                ai.generate_content(URL)
        self.assertFalse(self.audio.parent.exists())

    def test_validated_generated_content(self):
        """Well-formed model output preserves the correct solutions."""
        content = quiz_content()
        self.assertEqual(
            validate_generated_content(json.dumps(content)), content
        )
        schema = generation_config()['response_json_schema']
        self.assertEqual(schema['properties']['questions']['minItems'], 10)
        self.assertEqual(schema['properties']['questions']['maxItems'], 10)

    def test_invalid_model_output(self):
        """Reject malformed JSON, counts and solution flags."""
        invalid = quiz_content()
        invalid['questions'][0]['answers'][0]['is_correct'] = False
        for text in ['not json', '{}', 'null', '[]', json.dumps(invalid)]:
            with self.assertRaises(ai.GenerationFailed):
                validate_generated_content(text)

    @override_settings(OPENAI_API_KEY='test')
    def test_whisper_request_and_file_closure(self):
        """Whisper receives a binary stream that is closed after the call."""
        with (
            TemporaryDirectory() as directory,
            patch.object(ai, 'OpenAI') as sdk,
        ):
            path = self.fake_download(URL, directory)
            client = sdk.return_value.__enter__.return_value
            client.audio.transcriptions.create.return_value.text = 'Transcript'
            self.assertEqual(ai.transcribe_audio(path), 'Transcript')
            args = client.audio.transcriptions.create.call_args.kwargs
            self.assertEqual(args['model'], 'whisper-1')
            self.assertTrue(args['file'].closed)

    @override_settings(GEMINI_API_KEY='test', GEMINI_MODEL='gemini-2.5-flash')
    def test_gemini_receives_schema_and_validates_output(self):
        """The configured Flash model receives the schema and transcript."""
        with patch.object(ai.genai, 'Client') as sdk:
            client = sdk.return_value.__enter__.return_value
            client.models.generate_content.return_value = SimpleNamespace(
                text=json.dumps(quiz_content())
            )
            self.assertEqual(
                ai.generate_questions('Transcript'), quiz_content()
            )
            self.check_gemini_arguments(client)

    def check_gemini_arguments(self, client):
        """Check the provider request independently of output parsing."""
        args = client.models.generate_content.call_args.kwargs
        self.assertEqual(args['model'], 'gemini-2.5-flash')
        self.assertEqual(args['contents'], 'Transcript')
        self.assertEqual(
            args['config']['response_mime_type'], 'application/json'
        )


class GenerationAPITests(APITestCase):
    def setup_test(self):
        """Authenticate an owner for generated quiz creation."""
        self.user = get_user_model().objects.create_user(
            username='owner', email='owner@example.com'
        )
        self.client.force_authenticate(self.user)

    setUp = setup_test

    def test_generated_quiz_is_persisted(self):
        """Generation saves ten questions and ten correct solutions."""
        with patch.object(ai, 'generate_content', return_value=quiz_content()):
            response = self.client.post('/api/quizzes/', {'youtube_url': URL})
        self.assertEqual(response.status_code, 201)
        quiz = Quiz.objects.get()
        self.assertEqual(quiz.questions.count(), 10)
        self.assertEqual(
            sum(
                q.answers.filter(is_correct=True).count()
                for q in quiz.questions.all()
            ),
            10,
        )

    def test_invalid_url_never_calls_provider(self):
        """URL validation happens before the external pipeline."""
        with patch.object(ai, 'generate_content') as generate:
            response = self.client.post(
                '/api/quizzes/', {'youtube_url': 'https://evil.example/video'}
            )
        self.assertEqual(response.status_code, 400)
        generate.assert_not_called()
        self.assertFalse(Quiz.objects.exists())

    @override_settings(OPENAI_API_KEY='', GEMINI_API_KEY='')
    def test_missing_credentials_returns_safe_503(self):
        """Missing keys return a clear failure and leave no partial quiz."""
        response = self.client.post('/api/quizzes/', {'youtube_url': URL})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(Quiz.objects.exists())

    def test_generation_failure_leaves_no_quiz(self):
        """Failed upstream services cannot persist partial content."""
        with patch.object(
            ai, 'generate_content', side_effect=ai.GenerationFailed
        ):
            response = self.client.post('/api/quizzes/', {'youtube_url': URL})
        self.assertEqual(response.status_code, 502)
        self.assertFalse(Quiz.objects.exists())

    def test_database_failure_rolls_back_content(self):
        """Roll back all quiz data if storage fails midway."""
        with patch(
            'apps.quizzes.services.save_question',
            side_effect=RuntimeError('storage'),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    '/api/quizzes/',
                    {**quiz_content(), 'youtube_url': URL},
                    format='json',
                )
        self.assertFalse(Quiz.objects.exists())
