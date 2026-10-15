"""Owner-scoped CRUD and automatically saved quiz play."""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Quiz
from .permissions import IsQuizOwner
from .serializers import (
    ProgressSerializer,
    QuizCreateSerializer,
    QuizEditSerializer,
    QuizSerializer,
    SelectionSerializer,
)
from .services import filter_period, replay_quiz, save_selection


class OwnedQuizMixin:
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]

    def get_queryset(self):
        """Load quizzes before applying the ownership object permission."""
        return (
            Quiz.objects.all()
            .select_related('progress')
            .prefetch_related(
                'questions__answers', 'progress__selections__answer'
            )
        )


class QuizListCreateView(OwnedQuizMixin, generics.ListCreateAPIView):
    def get_queryset(self):
        """Filter owned quizzes by an optional local calendar period."""
        return filter_period(
            super().get_queryset().filter(owner=self.request.user),
            self.request.query_params.get('period'),
        )

    def create(self, request, *args, **kwargs):
        """Validate inputs before generating or storing quiz content."""
        from .generation import create_quiz

        serializer = QuizCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quiz = create_quiz(request.user, serializer.validated_data)
        return Response(QuizSerializer(quiz).data, status=201)


class QuizDetailView(OwnedQuizMixin, generics.RetrieveUpdateDestroyAPIView):
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def update(self, request, *args, **kwargs):
        """Limit edits to title and description."""
        quiz = self.get_object()
        serializer = QuizEditSerializer(quiz, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(QuizSerializer(quiz).data)


class QuizProgressView(OwnedQuizMixin, generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        """Resume the saved attempt."""
        return Response(ProgressSerializer(self.get_object().progress).data)

    def patch(self, request, *args, **kwargs):
        """Persist one answer change and return updated progress."""
        quiz = self.get_object()
        serializer = SelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        progress = save_selection(quiz, serializer.validated_data)
        return Response(ProgressSerializer(progress).data)


class QuizReplayView(OwnedQuizMixin, generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        """Start a fresh attempt on the same owned quiz."""
        return Response(
            ProgressSerializer(replay_quiz(self.get_object())).data
        )


quiz_list_create = QuizListCreateView.as_view()
quiz_detail = QuizDetailView.as_view()
