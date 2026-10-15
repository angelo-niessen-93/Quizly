"""Keep existing quiz URLs and add progress and replay actions."""

from django.urls import path

from . import views

app_name = 'quizzes'

urlpatterns = [
    path('quizzes/', views.quiz_list_create, name='quiz-list-create'),
    path('quizzes/<int:pk>/', views.quiz_detail, name='quiz-detail'),
    path(
        'quizzes/<int:pk>/progress/',
        views.QuizProgressView.as_view(),
        name='quiz-progress',
    ),
    path(
        'quizzes/<int:pk>/replay/',
        views.QuizReplayView.as_view(),
        name='quiz-replay',
    ),
]
