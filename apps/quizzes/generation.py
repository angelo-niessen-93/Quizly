"""Coordinate quiz generation and validated persistence."""

from .serializers import QuizContentSerializer
from .services import save_quiz


def create_quiz(owner, data):
    """Use supplied questions or generate them from the YouTube audio."""
    data = data.copy()
    video_url = data.pop('video_url')
    if 'questions' not in data:
        from .ai import generate_content

        data = {**generate_content(video_url), **data}
    data.setdefault('title', 'Quiz')
    data.setdefault('description', '')
    serializer = QuizContentSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return save_quiz(owner, video_url, serializer.validated_data)
