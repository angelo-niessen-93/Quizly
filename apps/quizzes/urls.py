from django.urls import path

from . import views

app_name = 'quizzes'

urlpatterns = [
    path('quizzes/', views.quiz_list_create, name='quiz-list-create'),
    path('quizzes/<int:pk>/', views.quiz_detail, name='quiz-detail'),
]
