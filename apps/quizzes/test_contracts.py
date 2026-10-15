"""Exact quiz contracts supplied from the academy endpoint documentation."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APITestCase

from . import ai
from .models import Answer, Progress, Question, Quiz, SelectedAnswer
from .services import save_quiz
from .tests import FOREIGN_ROUTES, URL, quiz_content

QUIZ_FIELDS = {
    'id',
    'title',
    'description',
    'created_at',
    'updated_at',
    'video_url',
    'questions',
}
QUESTION_FIELDS = {
    'id',
    'question_title',
    'question_options',
    'answer',
    'created_at',
    'updated_at',
}


class QuizContractTests(APITestCase):
    def setup_test(self):
        """Create owned and foreign quizzes without calling providers."""
        self.owner = get_user_model().objects.create_user(
            username='owner', email='owner@example.com'
        )
        self.other = get_user_model().objects.create_user(
            username='other', email='other@example.com'
        )
        self.quiz = save_quiz(self.owner, URL, quiz_content())
        self.foreign = save_quiz(self.other, URL, quiz_content())
        self.detail = f'/api/quizzes/{self.quiz.pk}/'
        self.client.force_authenticate(self.owner)

    setUp = setup_test

    def assert_quiz_contract(self, data, quiz):
        """Reject extra fields and validate all ten question contracts."""
        self.assertEqual(set(data), QUIZ_FIELDS)
        self.assert_quiz_metadata(data, quiz)
        self.assertIs(type(data['questions']), list)
        self.assertEqual(len(data['questions']), 10)
        stored = quiz.questions.all()
        for item, question in zip(data['questions'], stored, strict=True):
            self.assert_question_contract(item, question)

    def assert_quiz_metadata(self, data, quiz):
        """Verify public quiz identity, text and stored video URL."""
        self.assertIs(type(data['id']), int)
        self.assertEqual(data['id'], quiz.pk)
        for field in ('title', 'description', 'video_url'):
            self.assertIs(type(data[field]), str)
            self.assertEqual(data[field], getattr(quiz, field))
        self.assert_timestamps(data, quiz)

    def assert_question_contract(self, data, question):
        """Check question identity, public field names and timestamps."""
        self.assertEqual(set(data), QUESTION_FIELDS)
        self.assertIs(type(data['id']), int)
        self.assertEqual(data['id'], question.pk)
        self.assertIs(type(data['question_title']), str)
        self.assertEqual(data['question_title'], question.question)
        self.assert_answer_contract(data, question)
        self.assert_timestamps(data, question)

    def assert_answer_contract(self, data, question):
        """Require four text options and the actual correct answer text."""
        options = data['question_options']
        self.assertIs(type(options), list)
        self.assertEqual(len(options), 4)
        self.assertTrue(all(type(option) is str for option in options))
        expected = list(question.answers.values_list('text', flat=True))
        self.assertEqual(options, expected)
        self.assertIs(type(data['answer']), str)
        self.assertIn(data['answer'], options)
        self.assertEqual(
            data['answer'], question.answers.get(is_correct=True).text
        )

    def assert_timestamps(self, data, instance):
        """Require aware ISO-8601 dates matching stored timestamps."""
        for field in ('created_at', 'updated_at'):
            self.assertIs(type(data[field]), str)
            parsed = parse_datetime(data[field])
            self.assertIsNotNone(parsed)
            self.assertTrue(timezone.is_aware(parsed))
            self.assertEqual(parsed, getattr(instance, field))

    def test_create_from_documented_url_request(self):
        """The documented url request generates the exact 201 quiz response."""
        with patch.object(
            ai, 'generate_content', return_value=quiz_content()
        ) as run:
            response = self.client.post(
                '/api/quizzes/', {'url': URL}, format='json'
            )
        self.assertEqual(response.status_code, 201)
        run.assert_called_once_with(URL)
        quiz = Quiz.objects.get(pk=response.json()['id'])
        self.assertEqual(quiz.owner, self.owner)
        self.assertEqual(quiz.video_url, URL)
        self.assert_quiz_contract(response.json(), quiz)

    def test_list_contains_only_owned_quizzes(self):
        """List only owned quiz objects in the documented format."""
        response = self.client.get('/api/quizzes/')
        self.assertEqual(response.status_code, 200)
        self.assertIs(type(response.json()), list)
        self.assertEqual(len(response.json()), 1)
        self.assert_quiz_contract(response.json()[0], self.quiz)

    def test_list_without_owned_quizzes_is_empty(self):
        """A new account sees an empty array rather than foreign content."""
        self.quiz.delete()
        response = self.client.get('/api/quizzes/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_detail_uses_exact_contract(self):
        """Detail has no legacy fields or embedded progress extension."""
        response = self.client.get(self.detail)
        self.assertEqual(response.status_code, 200)
        self.assert_quiz_contract(response.json(), self.quiz)

    def test_patch_uses_exact_contract_and_updates_timestamp(self):
        """Metadata edits preserve creation dates and the documented shape."""
        created = self.quiz.created_at
        updated = self.quiz.updated_at + timedelta(seconds=1)
        with patch('django.utils.timezone.now', return_value=updated):
            response = self.client.patch(
                self.detail, {'title': 'Edited', 'description': 'New'}
            )
        self.assert_metadata_patch(response, created, updated)

    def test_patch_does_not_change_question_timestamps(self):
        """Editing quiz metadata leaves question content dates unchanged."""
        before = list(
            self.quiz.questions.values_list('pk', 'created_at', 'updated_at')
        )
        self.client.patch(self.detail, {'title': 'Edited'})
        after = list(
            self.quiz.questions.values_list('pk', 'created_at', 'updated_at')
        )
        self.assertEqual(after, before)

    def test_partial_metadata_update(self):
        """PATCH accepts one editable field and preserves the other."""
        response = self.client.patch(self.detail, {'title': 'Only title'})
        self.assertEqual(response.status_code, 200)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.description, 'Description')
        self.assert_quiz_contract(response.json(), self.quiz)

    def test_delete_has_no_response_body(self):
        """Delete returns 204 and cascades through all owned quiz content."""
        ids = list(self.quiz.questions.values_list('id', flat=True))
        self.select_first_answer()
        response = self.client.delete(self.detail)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assert_deleted_content(ids)

    def assert_object_status(self, base, expected):
        """Check all object routes using their allowed methods."""
        for method, suffix in FOREIGN_ROUTES:
            with self.subTest(method=method, suffix=suffix):
                response = getattr(self.client, method)(base + suffix, {})
                self.assertEqual(response.status_code, expected)

    def test_foreign_objects_are_403(self):
        """Existing quizzes owned by another user consistently return 403."""
        self.assert_object_status(f'/api/quizzes/{self.foreign.pk}/', 403)
        self.assertTrue(Quiz.objects.filter(pk=self.foreign.pk).exists())

    def test_missing_objects_are_404(self):
        """Nonexistent quiz IDs consistently return 404."""
        self.assert_object_status(
            f'/api/quizzes/{self.foreign.pk + 1000}/', 404
        )

    def test_anonymous_requests_are_401(self):
        """All protected quiz routes require authentication."""
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/quizzes/').status_code, 401)
        self.assertEqual(
            self.client.post('/api/quizzes/', {}).status_code, 401
        )
        self.assert_object_status(self.detail, 401)

    def test_invalid_access_cookie_is_401(self):
        """Invalid cookie tokens cannot read or generate quiz content."""
        self.client.force_authenticate(None)
        self.client.cookies['access_token'] = 'not-a-valid-jwt'
        self.assertEqual(self.client.get('/api/quizzes/').status_code, 401)
        self.assertEqual(
            self.client.post('/api/quizzes/', {}).status_code, 401
        )

    def test_create_requires_url_request_field(self):
        """Require url rather than the response or database field name."""
        with patch.object(ai, 'generate_content') as run:
            for data in ({}, {'video_url': URL}, {'youtube_url': URL}):
                response = self.client.post(
                    '/api/quizzes/', data, format='json'
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn('url', response.json())
        run.assert_not_called()

    def test_invalid_urls_return_400_without_provider_calls(self):
        """Bad URL values fail before external processing."""
        with patch.object(ai, 'generate_content') as run:
            for url in ('', 'invalid', 'https://evil.example/video', None, []):
                response = self.client.post(
                    '/api/quizzes/', {'url': url}, format='json'
                )
                self.assertEqual(response.status_code, 400)
        run.assert_not_called()

    def test_invalid_metadata_returns_400(self):
        """Malformed title and description values are validation errors."""
        for data in (
            {'title': ''},
            {'title': 'x' * 201},
            {'description': None},
            {'description': 'x' * 5001},
        ):
            response = self.client.patch(self.detail, data, format='json')
            self.assertEqual(response.status_code, 400)

    def test_progress_keeps_score_selections_and_option_ids(self):
        """Saved play remains usable outside the exact quiz response."""
        response = self.client.get(self.detail + 'progress/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['attempt'], 1)
        self.assertEqual(response.json()['selections'], [])
        self.assertIsNone(response.json()['score'])
        question = response.json()['questions'][0]
        self.assertEqual(len(question['answers']), 4)
        self.assertIs(type(question['answers'][0]['id']), int)
        self.assertIsNone(question['correct_answer'])

    def test_answer_text_is_available_before_completion(self):
        """Include the correct answer text in every public quiz response."""
        self.assertFalse(self.quiz.progress.completed)
        response = self.client.get(self.detail)
        for item in response.json()['questions']:
            self.assertIs(type(item['answer']), str)
            self.assertIn(item['answer'], item['question_options'])

    def test_internal_error_returns_500_without_partial_quiz(self):
        """Unexpected storage errors remain 500 and roll back quiz creation."""
        self.client.raise_request_exception = False
        with patch.object(ai, 'generate_content', return_value=quiz_content()):
            with patch(
                'apps.quizzes.services.save_question',
                side_effect=RuntimeError('private storage details'),
            ):
                response = self.client.post('/api/quizzes/', {'url': URL})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b'private storage details', response.content)
        self.assertEqual(Quiz.objects.count(), 2)

    def test_generation_failure_preserves_external_error_code(self):
        """Return 502 for upstream failures."""
        with patch.object(
            ai, 'generate_content', side_effect=ai.GenerationFailed
        ):
            response = self.client.post('/api/quizzes/', {'url': URL})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(Quiz.objects.count(), 2)

    def assert_metadata_patch(self, response, created, updated):
        """Verify saved metadata and creation/update timestamp semantics."""
        self.assertEqual(response.status_code, 200)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.created_at, created)
        self.assertEqual(self.quiz.updated_at, updated)
        self.assertEqual(
            (self.quiz.title, self.quiz.description), ('Edited', 'New')
        )
        self.assert_quiz_contract(response.json(), self.quiz)

    def select_first_answer(self):
        """Persist a selection before exercising cascading deletion."""
        question = self.quiz.questions.first()
        response = self.client.patch(
            self.detail + 'progress/',
            {'question': question.pk, 'answer': question.answers.first().pk},
        )
        self.assertEqual(response.status_code, 200)

    def assert_deleted_content(self, ids):
        """Verify cascading removal of content and saved progress."""
        self.assertFalse(Quiz.objects.filter(pk=self.quiz.pk).exists())
        self.assertFalse(Question.objects.filter(pk__in=ids).exists())
        self.assertFalse(Answer.objects.filter(question_id__in=ids).exists())
        self.assertFalse(
            Progress.objects.filter(quiz_id=self.quiz.pk).exists()
        )
        self.assertFalse(
            SelectedAnswer.objects.filter(question_id__in=ids).exists()
        )
