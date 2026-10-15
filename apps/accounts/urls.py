from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('csrf/', views.csrf, name='csrf'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('token/refresh/', views.token_refresh, name='token-refresh'),
]
