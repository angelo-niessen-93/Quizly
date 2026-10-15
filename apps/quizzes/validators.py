"""Restrict input to canonical, single-video YouTube URLs."""

import re
from urllib.parse import parse_qs, urlsplit

from rest_framework.exceptions import ValidationError


def validate_youtube_url(value):
    """Canonicalize allowlisted hosts and valid eleven-character video IDs."""
    try:
        parts = urlsplit(value)
        video_id = extract_video_id(parts)
    except (ValueError, TypeError):
        raise ValidationError('Enter a valid YouTube video URL.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id or ''):
        raise ValidationError('Enter a valid YouTube video URL.')
    return 'https://www.youtube.com/watch?v=' + video_id


def extract_video_id(parts):
    """Reject credentials, ports, fragments and unsupported hosts."""
    if (
        parts.scheme != 'https'
        or parts.username is not None
        or parts.port is not None
        or parts.fragment
    ):
        return None
    if parts.hostname == 'youtu.be' and parts.path.count('/') == 1:
        return parts.path.removeprefix('/')
    if parts.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        return youtube_video_id(parts)
    return None


def youtube_video_id(parts):
    """Read a single watch ID or a supported embedded video path."""
    if parts.path == '/watch':
        values = parse_qs(parts.query).get('v', [])
        return values[0] if len(values) == 1 else None
    if re.fullmatch(r'/(shorts|embed)/[A-Za-z0-9_-]{11}', parts.path):
        return parts.path.rsplit('/', 1)[1]
    return None
