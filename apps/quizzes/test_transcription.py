"""Regression tests for local Whisper caching, device choice and failures."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from . import ai, transcription


class LocalWhisperTests(SimpleTestCase):
    def setup_test(self):
        """Isolate the model cache without loading real weights."""
        transcription.load_whisper_model.cache_clear()
        self.addCleanup(transcription.load_whisper_model.cache_clear)
        self.model = Mock()
        self.model.device = SimpleNamespace(type='cuda')
        self.model.transcribe.return_value = {'text': ' Local transcript '}

    setUp = setup_test

    @override_settings(WHISPER_MODEL='small', WHISPER_DEVICE='cuda')
    def test_small_model_is_loaded_once(self):
        """Repeated transcriptions reuse the same cached model."""
        with patch.object(
            transcription.whisper, 'load_model', return_value=self.model
        ) as load:
            self.assertEqual(
                ai.transcribe_audio(Path('first.wav')), 'Local transcript'
            )
            self.assertEqual(
                ai.transcribe_audio(Path('second.wav')), 'Local transcript'
            )
        self.assertEqual(load.call_count, 1)
        self.assertEqual(load.call_args.args, ('small',))
        self.assertEqual(load.call_args.kwargs['device'], 'cuda')

    def test_concurrent_requests_share_one_model(self):
        """The inference lock prevents duplicate loads on parallel requests."""
        with patch.object(
            transcription.whisper, 'load_model', return_value=self.model
        ) as load:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(
                    pool.map(
                        transcription.transcribe_local,
                        [Path('one.wav'), Path('two.wav')],
                    )
                )
        self.assertEqual(results, ['Local transcript', 'Local transcript'])
        self.assertEqual(load.call_count, 1)

    def test_cuda_uses_half_precision(self):
        """CUDA inference uses FP16 with a local filename."""
        with patch.object(
            transcription.whisper, 'load_model', return_value=self.model
        ):
            ai.transcribe_audio(Path('speech.wav'))
        self.model.transcribe.assert_called_once_with(
            'speech.wav', fp16=True, verbose=False
        )

    def test_cpu_disables_half_precision(self):
        """CPU inference explicitly avoids unsupported FP16 processing."""
        self.model.device = SimpleNamespace(type='cpu')
        with patch.object(
            transcription.whisper, 'load_model', return_value=self.model
        ):
            ai.transcribe_audio(Path('speech.wav'))
        self.assertFalse(self.model.transcribe.call_args.kwargs['fp16'])

    @override_settings(WHISPER_DEVICE='auto')
    def test_automatic_device_selection(self):
        """Auto selects CUDA only when PyTorch reports it available."""
        for available, expected in ((True, 'cuda'), (False, 'cpu')):
            with patch.object(
                transcription.torch.cuda,
                'is_available',
                return_value=available,
            ):
                self.assertEqual(transcription.whisper_device(), expected)

    def test_empty_transcription_is_rejected(self):
        """Silent or empty results cannot be passed to quiz generation."""
        self.model.transcribe.return_value = {'text': ' '}
        with patch.object(
            transcription.whisper, 'load_model', return_value=self.model
        ):
            with self.assertRaises(ai.GenerationFailed):
                ai.transcribe_audio(Path('silent.wav'))

    @override_settings(GEMINI_API_KEY='configured', OPENAI_API_KEY='')
    def test_no_openai_key_is_required(self):
        """The generation preflight needs Gemini and local audio tools only."""
        with patch.object(ai, 'which', return_value='installed-tool'):
            ai.require_configuration()

    def test_failed_model_load_can_be_retried(self):
        """An unsuccessful model load is never cached as a working model."""
        with patch.object(
            transcription.whisper,
            'load_model',
            side_effect=[RuntimeError('load'), self.model],
        ) as load:
            with self.assertRaises(RuntimeError):
                transcription.transcribe_local(Path('speech.wav'))
            self.assertEqual(
                transcription.transcribe_local(Path('speech.wav')),
                'Local transcript',
            )
        self.assertEqual(load.call_count, 2)
