"""Distinguish forbidden existing quizzes from nonexistent quiz IDs."""

from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        """Only the owner may read, modify or play an existing quiz."""
        return obj.owner_id == request.user.pk
