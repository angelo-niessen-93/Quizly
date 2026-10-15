"""Quiz content and the owner's automatically saved current attempt."""

from django.conf import settings
from django.db import models


class Quiz(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quizzes',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, max_length=5000)
    video_url = models.URLField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def __str__(self):
        """Identify a quiz in admin selectors."""
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name='questions'
    )
    question = models.CharField(max_length=1000)
    position = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(
                fields=['quiz', 'position'], name='unique_question_position'
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1, position__lte=10),
                name='question_position_range',
            ),
        ]

    def __str__(self):
        """Identify a question in admin selectors."""
        return self.question


class Answer(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name='answers'
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(
                fields=['question', 'position'], name='unique_answer_position'
            ),
            models.UniqueConstraint(
                fields=['question'],
                condition=models.Q(is_correct=True),
                name='one_correct_answer',
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1, position__lte=4),
                name='answer_position_range',
            ),
        ]

    def __str__(self):
        """Identify an answer in admin selectors."""
        return self.text


class Progress(models.Model):
    quiz = models.OneToOneField(
        Quiz, on_delete=models.CASCADE, related_name='progress'
    )
    attempt = models.PositiveIntegerField(default=1)
    completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class SelectedAnswer(models.Model):
    progress = models.ForeignKey(
        Progress, on_delete=models.CASCADE, related_name='selections'
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['progress', 'question'],
                name='one_selection_per_question',
            )
        ]
