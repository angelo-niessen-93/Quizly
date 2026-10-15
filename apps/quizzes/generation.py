"""Coordinate quiz generation and validated persistence."""

from .serializers import QuizContentSerializer
from .services import save_quiz


def create_quiz(owner, data):
    """Use supplied questions or generate them from the YouTube audio."""
    data = data.copy()
    youtube_url = data.pop('youtube_url')
    if 'questions' not in data:
        from .ai import generate_content

        data = {**generate_content(youtube_url), **data}
    data.setdefault('title', 'Quiz')
    data.setdefault('description', '')
    serializer = QuizContentSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return save_quiz(owner, youtube_url, serializer.validated_data)
