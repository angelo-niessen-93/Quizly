"""Atomic content creation, date filtering and persisted quiz attempts."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Answer, Progress, Question, Quiz, SelectedAnswer


def filter_period(queryset, period):
    """Select local calendar days, including today in the seven-day window."""
    if not period:
        return queryset
    if period not in ('today', 'week'):
        raise ValidationError({'period': 'Choose today or week.'})
    today = timezone.localdate()
    start = today - timedelta(days=6 if period == 'week' else 0)
    return queryset.filter(created_at__date__range=(start, today))


@transaction.atomic
def save_quiz(owner, youtube_url, content):
    """Persist a validated quiz and initial progress as a single unit."""
    content = content.copy()
    questions = content.pop('questions')
    quiz = Quiz.objects.create(owner=owner, youtube_url=youtube_url, **content)
    for position, item in enumerate(questions, 1):
        save_question(quiz, position, item)
    Progress.objects.create(quiz=quiz)
    return quiz


def save_question(quiz, position, item):
    """Persist a question with its four validated choices."""
    question = Question.objects.create(
        quiz=quiz, position=position, question=item['question']
    )
    Answer.objects.bulk_create(
        [
            Answer(question=question, position=index, **answer)
            for index, answer in enumerate(item['answers'], 1)
        ]
    )


def validate_selection(quiz, data):
    """Prevent cross-quiz questions and answers from being submitted."""
    answer = Answer.objects.filter(
        pk=data['answer'], question_id=data['question'], question__quiz=quiz
    ).first()
    if answer is None:
        raise ValidationError('Answer does not belong to this quiz question.')
    return answer


@transaction.atomic
def save_selection(quiz, data):
    """Automatically save or replace one answer and update completion."""
    quiz = Quiz.objects.select_for_update().get(pk=quiz.pk)
    answer = validate_selection(quiz, data)
    progress = quiz.progress
    SelectedAnswer.objects.update_or_create(
        progress=progress,
        question=answer.question,
        defaults={'answer': answer},
    )
    progress.completed = progress.selections.count() == quiz.questions.count()
    progress.save(update_fields=['completed', 'updated_at'])
    return progress


@transaction.atomic
def replay_quiz(quiz):
    """Clear the current attempt and conceal solutions for another play."""
    quiz = Quiz.objects.select_for_update().get(pk=quiz.pk)
    progress = quiz.progress
    progress.selections.all().delete()
    progress.attempt += 1
    progress.completed = False
    progress.save(update_fields=['attempt', 'completed', 'updated_at'])
    return progress
