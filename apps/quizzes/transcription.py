"""Reuse one local Whisper model per process and serialize GPU inference."""

from functools import lru_cache
from threading import RLock

import torch
import whisper
from django.conf import settings

MODEL_LOCK = RLock()


def whisper_device():
    """Choose CUDA when available unless explicitly configured otherwise."""
    if settings.WHISPER_DEVICE != 'auto':
        return settings.WHISPER_DEVICE
    return 'cuda' if torch.cuda.is_available() else 'cpu'


@lru_cache(maxsize=1)
def load_whisper_model():
    """Cache the configured model after its first successful load."""
    return whisper.load_model(
        settings.WHISPER_MODEL,
        device=whisper_device(),
        download_root=str(settings.WHISPER_CACHE_DIR),
    )


def transcribe_local(path):
    """Load and transcribe under one lock to avoid duplicate model loads."""
    with MODEL_LOCK:
        model = load_whisper_model()
        result = model.transcribe(
            str(path), fp16=model.device.type == 'cuda', verbose=False
        )
    return result.get('text', '').strip()
