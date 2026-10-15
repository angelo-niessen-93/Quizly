"""Bounded YouTube audio processing, Whisper and Gemini orchestration."""

from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory

from django.conf import settings
from google import genai
from google.genai.errors import APIError as GeminiError
from httpx import HTTPError
from openai import APIError as OpenAIError
from openai import OpenAI
from rest_framework.exceptions import APIException, ValidationError
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .ai_schema import generation_config, validate_generated_content
from .validators import validate_youtube_url


class GenerationUnavailable(APIException):
    status_code = 503
    default_detail = 'Quiz generation is not configured.'
    default_code = 'generation_unavailable'


class GenerationFailed(APIException):
    status_code = 502
    default_detail = 'Quiz generation failed. Please try again later.'
    default_code = 'generation_failed'


def require_configuration():
    """Fail before downloading when keys or audio tools are missing."""
    if not settings.OPENAI_API_KEY or not settings.GEMINI_API_KEY:
        raise GenerationUnavailable()
    folder = (
        Path(settings.FFMPEG_LOCATION) if settings.FFMPEG_LOCATION else None
    )
    for tool in ('ffmpeg', 'ffprobe'):
        if not which(str(folder / tool) if folder else tool):
            raise GenerationUnavailable('Audio processing is not configured.')


def download_options(directory):
    """Combine bounded audio settings with a fixed temporary output path."""
    return {
        **DOWNLOAD_OPTIONS,
        'outtmpl': str(Path(directory) / 'audio.%(ext)s'),
        'ffmpeg_location': settings.FFMPEG_LOCATION or None,
    }


def validate_video(info):
    """Reject live, unknown-duration and overly long videos before download."""
    duration = info.get('duration')
    if (
        info.get('is_live')
        or not isinstance(duration, (int, float))
        or not 0 < duration <= settings.MAX_VIDEO_SECONDS
    ):
        raise ValidationError(
            'Use a recorded YouTube video of at most 20 minutes.'
        )


def download_audio(url, directory):
    """Inspect metadata before processing audio through FFmpeg."""
    with YoutubeDL(download_options(directory)) as downloader:
        info = downloader.extract_info(url, download=False)
        validate_video(info)
        downloader.process_ie_result(info, download=True)
    path = Path(directory) / 'audio.mp3'
    if not path.is_file() or not 0 < path.stat().st_size < 24 * 1024 * 1024:
        raise GenerationFailed()
    return path


def transcribe_audio(path):
    """Send a closed-after-use audio stream to the Whisper API."""
    with OpenAI(
        api_key=settings.OPENAI_API_KEY, timeout=90, max_retries=1
    ) as client:
        with path.open('rb') as audio:
            result = client.audio.transcriptions.create(
                model='whisper-1', file=audio
            )
    if not result.text or not result.text.strip():
        raise GenerationFailed()
    return result.text.strip()


def generate_questions(transcript):
    """Ask Gemini Flash for schema-constrained quiz content."""
    with genai.Client(
        api_key=settings.GEMINI_API_KEY, http_options={'timeout': 90000}
    ) as client:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=transcript,
            config=generation_config(),
        )
    return validate_generated_content(response.text)


def generate_content(url):
    """Clean all temporary files on success and every exceptional exit."""
    url = validate_youtube_url(url)
    require_configuration()
    try:
        with TemporaryDirectory(prefix='quizly-') as directory:
            path = download_audio(url, directory)
            transcript = transcribe_audio(path)
            return generate_questions(transcript)
    except GENERATION_ERRORS:
        raise GenerationFailed() from None


DOWNLOAD_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'socket_timeout': 20,
    'retries': 1,
    'fragment_retries': 1,
    'max_filesize': 100 * 1024 * 1024,
    'postprocessors': [
        {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64',
        }
    ],
}


GENERATION_ERRORS = (
    DownloadError,
    OpenAIError,
    GeminiError,
    HTTPError,
    OSError,
    ValueError,
)
