"""Validate content and expose solutions only after completing an attempt."""

from rest_framework import serializers

from .models import Answer, Progress, Question, Quiz, SelectedAnswer
from .validators import validate_youtube_url


class AnswerInputSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=500)
    is_correct = serializers.BooleanField()


class QuestionInputSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=1000)
    answers = AnswerInputSerializer(many=True, min_length=4, max_length=4)

    def validate_answers(self, answers):
        """Require distinct choices and exactly one correct answer."""
        if sum(answer['is_correct'] for answer in answers) != 1:
            raise serializers.ValidationError(
                'Exactly one answer must be correct.'
            )
        if len({answer['text'].casefold() for answer in answers}) != 4:
            raise serializers.ValidationError('Answer texts must be distinct.')
        return answers


class QuizContentSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=5000, allow_blank=True)
    questions = QuestionInputSerializer(
        many=True, min_length=10, max_length=10
    )

    def validate_questions(self, questions):
        """Reject repeated questions in supplied or generated content."""
        if len({item['question'].casefold() for item in questions}) != 10:
            raise serializers.ValidationError(
                'Question texts must be distinct.'
            )
        return questions


class QuizCreateSerializer(serializers.Serializer):
    youtube_url = serializers.CharField(max_length=200)
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )
    questions = QuestionInputSerializer(
        many=True, min_length=10, max_length=10, required=False
    )

    def validate_youtube_url(self, value):
        """Reject non-YouTube URLs before network processing."""
        return validate_youtube_url(value)

    def validate(self, attrs):
        """Apply the same content rules to manually supplied questions."""
        if 'questions' in attrs:
            content = QuizContentSerializer(
                data={
                    'title': attrs.get('title', 'Quiz'),
                    'description': attrs.get('description', ''),
                    'questions': attrs['questions'],
                }
            )
            content.is_valid(raise_exception=True)
        return attrs


class QuizEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ['title', 'description']


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'text']


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    correct_answer = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'question', 'position', 'answers', 'correct_answer']

    def get_correct_answer(self, question):
        """Reveal solutions only when the entire attempt is completed."""
        if question.quiz.progress.completed:
            return next(
                (a.pk for a in question.answers.all() if a.is_correct), None
            )
        return None


class SelectedAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SelectedAnswer
        fields = ['question', 'answer']


class ProgressSerializer(serializers.ModelSerializer):
    selections = SelectedAnswerSerializer(many=True, read_only=True)
    score = serializers.SerializerMethodField()

    class Meta:
        model = Progress
        fields = ['attempt', 'completed', 'updated_at', 'selections', 'score']

    def get_score(self, progress):
        """Return the percentage of correct answers after completion."""
        if not progress.completed:
            return None
        correct = sum(s.answer.is_correct for s in progress.selections.all())
        return round(correct / progress.quiz.questions.count() * 100, 2)


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    progress = ProgressSerializer(read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'youtube_url',
            'created_at',
            'questions',
            'progress',
        ]


class SelectionSerializer(serializers.Serializer):
    question = serializers.IntegerField(min_value=1)
    answer = serializers.IntegerField(min_value=1)
