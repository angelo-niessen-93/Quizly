"""Prepare an offline SDK request from the cached integration transcript."""

import json
import os
import sys
from functools import partial
from hashlib import sha256
from pathlib import Path

import django
import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizly.settings')
django.setup()

from django.conf import settings  # noqa: E402
from google import genai  # noqa: E402

from apps.quizzes.ai import gemini_http_options  # noqa: E402
from apps.quizzes.ai_schema import generation_config  # noqa: E402


def capture_request(request, manifest):
    """Capture only non-secret request settings in an in-memory transport."""
    manifest.update(
        offline=True,
        provider_requests=0,
        model=settings.GEMINI_MODEL,
        method=request.method,
        body=json.loads(request.content),
        server_timeout_seconds=int(request.headers['X-Server-Timeout']),
        httpx_timeout_seconds=request.extensions['timeout'],
    )
    return httpx.Response(200, json={'candidates': []})


def offline_client(manifest):
    """Create an SDK client that can only reach an in-memory transport."""
    options = gemini_http_options()
    options['client_args']['transport'] = httpx.MockTransport(
        partial(capture_request, manifest=manifest)
    )
    return genai.Client(
        api_key='offline-only', vertexai=False, http_options=options
    )


def prepare_request(transcript):
    """Serialize a real SDK request with no network and a dummy API key."""
    manifest = {}
    with offline_client(manifest) as client:
        client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=transcript,
            config=generation_config(),
        )
    return manifest


def main():
    """Save the prepared request in ignored cache, never call Gemini."""
    transcript = (ROOT / '.cache/flash38-transcript.txt').read_text('utf-8')
    manifest = prepare_request(transcript)
    manifest['transcript_sha256'] = sha256(transcript.encode()).hexdigest()
    path = ROOT / '.cache/gemini-next-request.json'
    path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Offline request prepared: {path}')
    print(f'Transcript characters: {len(transcript)}; provider requests: 0')


if __name__ == '__main__':
    main()
