"""Preserve existing content and progress across the contract migration."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from .tests import URL

LATEST = '0002_api_contract_fields'


def migrate_quizzes(name):
    """Migrate the quiz app and return its historical model registry."""
    executor = MigrationExecutor(connection)
    target = [('quizzes', name)]
    executor.migrate(target)
    return executor.loader.project_state(target).apps


def legacy_quiz(apps):
    """Create a pre-contract quiz with ten questions and saved selections."""
    quiz = legacy_quiz_row(apps)
    progress = apps.get_model('quizzes', 'Progress').objects.create(
        quiz_id=quiz.pk, attempt=3
    )
    for position in range(1, 11):
        question = legacy_question(apps, quiz, position)
        legacy_selection(apps, question, progress)
    return quiz.pk


def legacy_question(apps, quiz, position):
    """Populate one historical question with four answer choices."""
    question = apps.get_model('quizzes', 'Question').objects.create(
        quiz_id=quiz.pk, question=f'Question {position}', position=position
    )
    for number in range(1, 5):
        legacy_answer(apps, question, number)
    return question


class ContractMigrationTests(TransactionTestCase):
    def test_existing_url_content_and_progress_are_preserved(self):
        """Renaming the URL and adding timestamps never discards quiz data."""
        old_apps = migrate_quizzes('0001_initial')
        try:
            quiz_id = legacy_quiz(old_apps)
            new_apps = migrate_quizzes(LATEST)
            self.assert_preserved(new_apps, quiz_id)
        finally:
            migrate_quizzes(LATEST)

    def assert_preserved(self, apps, quiz_id):
        """Verify preserved metadata, relations and initialized timestamps."""
        quiz = apps.get_model('quizzes', 'Quiz').objects.get(pk=quiz_id)
        self.assertEqual(quiz.video_url, URL)
        self.assertEqual(
            (quiz.title, quiz.description), ('Legacy', 'Preserved')
        )
        self.assertIsNotNone(quiz.updated_at)
        self.assertEqual(quiz.questions.count(), 10)
        self.assertEqual(quiz.progress.attempt, 3)
        self.assertEqual(quiz.progress.selections.count(), 10)
        self.assert_preserved_questions(quiz)

    def assert_preserved_questions(self, quiz):
        """Check all question timestamps and answer counts after migration."""
        for question in quiz.questions.all():
            self.assertEqual(question.answers.count(), 4)
            self.assertIsNotNone(question.created_at)
            self.assertIsNotNone(question.updated_at)


def legacy_quiz_row(apps):
    """Create quiz metadata using the original youtube_url column."""
    user = apps.get_model('accounts', 'User').objects.create(
        username='legacy', email='legacy@example.com'
    )
    return apps.get_model('quizzes', 'Quiz').objects.create(
        owner_id=user.pk,
        title='Legacy',
        description='Preserved',
        youtube_url=URL,
    )


def legacy_answer(apps, question, number):
    """Create one ordered answer in the historical schema."""
    return apps.get_model('quizzes', 'Answer').objects.create(
        question_id=question.pk,
        position=number,
        text=f'Choice {number}',
        is_correct=number == 1,
    )


def legacy_selection(apps, question, progress):
    """Save a historical selection linked to its correct answer."""
    answer = apps.get_model('quizzes', 'Answer').objects.get(
        question_id=question.pk, is_correct=True
    )
    apps.get_model('quizzes', 'SelectedAnswer').objects.create(
        progress_id=progress.pk, question_id=question.pk, answer_id=answer.pk
    )
