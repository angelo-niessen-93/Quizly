"""Admin editing preserves quiz shape and single-solution constraints."""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.forms.models import inlineformset_factory
from django.test import TestCase

from .admin import AnswerForm, AnswerFormSet, QuestionAdmin, QuizAdmin
from .models import Answer, Question, Quiz
from .services import save_quiz
from .tests import URL, quiz_content


class QuizAdminTests(TestCase):
    def setup_test(self):
        """Prepare content and an answer formset matching the admin inline."""
        owner = get_user_model().objects.create_user(
            username='owner', email='owner@example.com'
        )
        self.quiz = save_quiz(owner, URL, quiz_content())
        self.question = self.quiz.questions.first()
        self.formset = answer_formset()

    setUp = setup_test

    def form_data(self, correct=0):
        """Build all four answer forms with one selected solution."""
        data = {'answers-TOTAL_FORMS': 4, 'answers-INITIAL_FORMS': 4}
        for index, answer in enumerate(self.question.answers.all()):
            prefix = f'answers-{index}-'
            data[prefix + 'id'] = answer.pk
            data[prefix + 'text'] = answer.text
            data[prefix + 'question'] = self.question.pk
            if index == correct:
                data[prefix + 'is_correct'] = 'on'
        return data

    def change_solution(self, correct):
        """Validate and persist a complete set of admin answer forms."""
        formset = self.formset(
            data=self.form_data(correct), instance=self.question
        )
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()

    def test_change_correct_answer_in_both_directions(self):
        """Moving the solution never violates the conditional unique index."""
        self.change_solution(3)
        self.assertEqual(
            self.question.answers.get(is_correct=True).position, 4
        )
        self.change_solution(0)
        self.assertEqual(
            self.question.answers.get(is_correct=True).position, 1
        )
        self.assertEqual(self.question.answers.count(), 4)

    def test_metadata_change_preserves_correct_answer(self):
        """Preserve the solution when only an answer text changes."""
        data = self.form_data()
        data['answers-2-text'] = 'Edited choice'
        formset = self.formset(data=data, instance=self.question)
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        self.assertEqual(
            self.question.answers.filter(is_correct=True).count(), 1
        )

    def test_invalid_solution_count_is_rejected(self):
        """Reject zero or multiple correct answers in admin."""
        for correct in (-1, 0):
            data = self.form_data(correct)
            if correct == 0:
                data['answers-1-is_correct'] = 'on'
            formset = self.formset(data=data, instance=self.question)
            self.assertFalse(formset.is_valid())

    def test_admin_keeps_content_shape(self):
        """Keep complete quiz content when editing in admin."""
        quiz_admin = QuizAdmin(Quiz, admin.site)
        question_admin = QuestionAdmin(Question, admin.site)
        self.assertFalse(quiz_admin.has_add_permission(None))
        self.assertFalse(question_admin.has_add_permission(None))
        self.assertFalse(question_admin.has_delete_permission(None))


def answer_formset():
    """Create validated answer forms for admin tests."""
    return inlineformset_factory(
        Question,
        Answer,
        form=AnswerForm,
        formset=AnswerFormSet,
        extra=0,
        fields=['text', 'is_correct'],
        min_num=4,
        max_num=4,
        can_delete=False,
    )
