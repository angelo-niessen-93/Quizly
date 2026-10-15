"""Quiz ownership, validation, saved progress and calendar regressions."""

from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Quiz, SelectedAnswer
from .services import save_quiz

URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'


def quiz_content():
    """Build ten distinct questions with four answers each."""
    return {
        'title': 'Example',
        'description': 'Description',
        'questions': [question_content(index) for index in range(10)],
    }


class QuizTests(APITestCase):
    def setup_test(self):
        """Create a user-owned quiz without making external requests."""
        self.user = get_user_model().objects.create_user(
            username='owner', email='owner@example.com', password='password'
        )
        self.quiz = save_quiz(self.user, URL, quiz_content())
        self.detail = f'/api/quizzes/{self.quiz.pk}/'
        self.client.force_authenticate(self.user)

    setUp = setup_test

    def select(self, question, correct=True):
        """Submit an answer through the progress API."""
        answer = question.answers.filter(is_correct=correct).first()
        return self.client.patch(
            self.detail + 'progress/',
            {'question': question.pk, 'answer': answer.pk},
            format='json',
        )

    def complete_quiz(self):
        """Answer every question correctly through the API."""
        for question in self.quiz.questions.all():
            self.select(question)

    def test_anonymous_access_is_denied(self):
        """Every quiz route requires authentication."""
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/quizzes/').status_code, 401)
        self.assertEqual(self.client.get(self.detail).status_code, 401)

    def test_owner_is_always_request_user(self):
        """Client owner fields cannot assign quizzes to another account."""
        data = {**quiz_content(), 'youtube_url': URL, 'owner': 999}
        response = self.client.post('/api/quizzes/', data, format='json')
        self.assertEqual(response.status_code, 201)
        quiz = Quiz.objects.get(pk=response.data['id'])
        self.assertEqual(quiz.owner, self.user)
        self.assertEqual(quiz.questions.count(), 10)
        self.assertTrue(
            all(q.answers.count() == 4 for q in quiz.questions.all())
        )

    def test_other_user_cannot_access_or_modify(self):
        """Foreign detail, progress and replay routes all return 404."""
        other = get_user_model().objects.create_user(
            username='other', email='other@example.com'
        )
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get('/api/quizzes/').data, [])
        self.check_foreign_routes()

    def test_edit_metadata_preserves_content(self):
        """Patch metadata without changing ownership or the video."""
        data = {
            'title': 'Edited',
            'description': 'New',
            'youtube_url': 'https://evil.example/',
        }
        response = self.client.patch(self.detail, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, 'Edited')
        self.assertEqual(self.quiz.description, 'New')
        self.assertEqual(self.quiz.youtube_url, URL)
        self.assertEqual(self.quiz.owner, self.user)

    def test_invalid_question_count(self):
        """A quiz cannot contain fewer or more than ten questions."""
        for count in (9, 11):
            data = quiz_content()
            data['questions'] = (data['questions'] * 2)[:count]
            response = self.client.post(
                '/api/quizzes/', {**data, 'youtube_url': URL}, format='json'
            )
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Quiz.objects.count(), 1)

    def test_invalid_answers(self):
        """Malformed choice counts, duplicates and solutions are rejected."""
        for mode in ('count', 'duplicate', 'correct'):
            data = quiz_content()
            make_invalid_answers(data['questions'][0]['answers'], mode)
            response = self.client.post(
                '/api/quizzes/', {**data, 'youtube_url': URL}, format='json'
            )
            self.assertEqual(response.status_code, 400)

    def test_solutions_are_hidden_until_complete(self):
        """Neither correctness flags nor correct answer IDs leak initially."""
        response = self.client.get(self.detail)
        for question in response.data['questions']:
            self.assertIsNone(question['correct_answer'])
            for answer in question['answers']:
                self.assertNotIn('is_correct', answer)
        self.assertIsNone(response.data['progress']['score'])

    def test_progress_is_saved_and_answer_replaceable(self):
        """Replacing an answer updates one persisted selection."""
        question = self.quiz.questions.first()
        self.select(question, False)
        response = self.select(question)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SelectedAnswer.objects.count(), 1)
        saved = self.client.get(self.detail + 'progress/').data
        self.assertEqual(len(saved['selections']), 1)
        self.assertEqual(
            saved['selections'][0]['answer'],
            question.answers.get(is_correct=True).pk,
        )

    def test_score_and_correct_solutions(self):
        """Completion yields a percentage and correct answer IDs."""
        self.complete_quiz()
        self.select(self.quiz.questions.first(), False)
        response = self.client.get(self.detail)
        self.assertTrue(response.data['progress']['completed'])
        self.assertEqual(response.data['progress']['score'], 90)
        for question in response.data['questions']:
            self.assertIsNotNone(question['correct_answer'])

    def test_foreign_answer_is_rejected(self):
        """A valid answer ID still must belong to the submitted question."""
        question, other = list(self.quiz.questions.all())[:2]
        response = self.client.patch(
            self.detail + 'progress/',
            {'question': question.pk, 'answer': other.answers.first().pk},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SelectedAnswer.objects.count(), 0)

    def test_replay_resets_progress_and_solutions(self):
        """Reset saved answers and conceal solutions on replay."""
        self.complete_quiz()
        response = self.client.post(self.detail + 'replay/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['attempt'], 2)
        self.assertEqual(response.data['selections'], [])
        self.assertFalse(response.data['completed'])
        detail = self.client.get(self.detail)
        self.assertIsNone(detail.data['questions'][0]['correct_answer'])

    def test_delete_cascades(self):
        """Deleting the quiz removes its questions, answers and progress."""
        question = self.quiz.questions.first()
        self.select(question)
        self.assertEqual(self.client.delete(self.detail).status_code, 204)
        self.assertFalse(Quiz.objects.exists())
        self.assertFalse(SelectedAnswer.objects.exists())
        self.assertEqual(self.client.get(self.detail).status_code, 404)

    def change_creation_day(self, days):
        """Set a deterministic local noon to avoid midnight races."""
        date = timezone.localdate() - timedelta(days=days)
        instant = timezone.make_aware(datetime.combine(date, time(12)))
        Quiz.objects.filter(pk=self.quiz.pk).update(created_at=instant)

    def test_calendar_filters(self):
        """The week contains today and the previous six local dates."""
        self.assertEqual(
            len(self.client.get('/api/quizzes/?period=today').data), 1
        )
        self.change_creation_day(6)
        self.assertEqual(
            self.client.get('/api/quizzes/?period=today').data, []
        )
        self.assertEqual(
            len(self.client.get('/api/quizzes/?period=week').data), 1
        )
        self.change_creation_day(7)
        self.assertEqual(self.client.get('/api/quizzes/?period=week').data, [])

    def test_invalid_period(self):
        """Unsupported filters cannot silently return misleading results."""
        self.assertEqual(
            self.client.get('/api/quizzes/?period=invalid').status_code, 400
        )

    @override_settings(TIME_ZONE='Europe/Berlin')
    def test_local_midnight_filter(self):
        """UTC timestamps are filtered according to the configured timezone."""
        today = timezone.localdate()
        instant = timezone.make_aware(datetime.combine(today, time.min))
        Quiz.objects.filter(pk=self.quiz.pk).update(created_at=instant)
        self.assertEqual(
            len(self.client.get('/api/quizzes/?period=today').data), 1
        )

    def check_foreign_routes(self):
        """Check all object endpoints against another user's quiz."""
        for method, suffix in FOREIGN_ROUTES:
            with self.subTest(method=method, suffix=suffix):
                response = getattr(self.client, method)(
                    self.detail + suffix, {}
                )
                self.assertEqual(response.status_code, 404)


def question_content(index):
    """Build one question with four distinct choices."""
    return {
        'question': f'Question {index}?',
        'answers': [
            {'text': f'Choice {choice}', 'is_correct': choice == 0}
            for choice in range(4)
        ],
    }


def make_invalid_answers(answers, mode):
    """Corrupt one independent aspect of valid test content."""
    if mode == 'count':
        answers.pop()
    elif mode == 'duplicate':
        answers[1]['text'] = answers[0]['text']
    else:
        answers[1]['is_correct'] = True


FOREIGN_ROUTES = [
    ('get', ''),
    ('patch', ''),
    ('delete', ''),
    ('get', 'progress/'),
    ('patch', 'progress/'),
    ('post', 'replay/'),
]
