"""Exercise the real SDK against an offline HTTP transport, never Google."""

import json
from unittest.mock import Mock, patch

import httpx
from django.test import SimpleTestCase, override_settings

from . import ai
from .tests import quiz_content


def provider_body(text=None, finish_reason='STOP'):
    """Build a provider envelope with a valid quiz unless overridden."""
    return {
        'candidates': [
            {
                'content': {
                    'role': 'model',
                    'parts': [{'text': text or json.dumps(quiz_content())}],
                },
                'finishReason': finish_reason,
            }
        ]
    }


@override_settings(
    GEMINI_API_KEY='offline-test-key',
    GEMINI_MODEL='gemini-3.8-flash',
    GEMINI_TIMEOUT_SECONDS=180,
    GEMINI_MAX_OUTPUT_TOKENS=8192,
)
class GeminiTransportTests(SimpleTestCase):
    def setup_test(self):
        """Install an in-memory responder for every provider request."""
        self.sdk_class = ai.genai.Client
        self.provider_request = Mock(
            return_value=httpx.Response(200, json=provider_body())
        )

    setUp = setup_test

    def offline_client(self, **kwargs):
        """Keep production options but replace the network transport."""
        kwargs['http_options']['client_args']['transport'] = (
            httpx.MockTransport(self.provider_request)
        )
        return self.sdk_class(**kwargs)

    def run_generation(self):
        """Send the production request through the real SDK offline."""
        with patch.object(ai.genai, 'Client', side_effect=self.offline_client):
            return ai.generate_questions('Transcript')

    def request_body(self):
        """Return the sole serialized provider payload after generation."""
        self.assertEqual(self.run_generation(), quiz_content())
        self.provider_request.assert_called_once()
        return json.loads(self.provider_request.call_args.args[0].content)

    def test_wire_thinking_and_output_limit(self):
        """Low thinking and the output cap survive SDK serialization."""
        config = self.request_body()['generationConfig']
        self.assertEqual(config['thinkingConfig']['thinking_level'], 'LOW')
        self.assertFalse(config['thinkingConfig']['include_thoughts'])
        self.assertEqual(config['maxOutputTokens'], 8192)
        self.assertEqual(config['responseMimeType'], 'application/json')

    def test_wire_schema_has_ten_questions_and_four_answers(self):
        """Preserve exact array sizes in the actual outgoing JSON schema."""
        config = self.request_body()['generationConfig']
        questions = config['responseJsonSchema']['properties']['questions']
        answers = questions['items']['properties']['answers']
        self.assertEqual(
            (questions['minItems'], questions['maxItems']), (10, 10)
        )
        self.assertEqual((answers['minItems'], answers['maxItems']), (4, 4))
        self.assertEqual(
            answers['items']['properties']['is_correct']['type'], 'boolean'
        )

    def test_server_deadline_precedes_httpx_timeout(self):
        """HTTPX has time to receive the explicit server deadline response."""
        self.run_generation()
        request = self.provider_request.call_args.args[0]
        self.assertEqual(request.headers['X-Server-Timeout'], '180')
        self.assertEqual(set(request.extensions['timeout'].values()), {190.0})
        self.assertIn('gemini-3.8-flash:generateContent', request.url.path)
        self.assertEqual(request.url.host, 'generativelanguage.googleapis.com')

    @override_settings(GEMINI_TIMEOUT_SECONDS=7, GEMINI_MAX_OUTPUT_TOKENS=4096)
    def test_configured_limits_reach_the_transport(self):
        """Custom deadlines and output caps keep their units and margin."""
        body = self.request_body()
        request = self.provider_request.call_args.args[0]
        self.assertEqual(request.headers['X-Server-Timeout'], '7')
        self.assertEqual(set(request.extensions['timeout'].values()), {17.0})
        self.assertEqual(body['generationConfig']['maxOutputTokens'], 4096)

    def test_http_errors_never_retry(self):
        """Quota, server and deadline errors each make one HTTP attempt."""
        for status in (408, 429, 500, 502, 503, 504):
            with self.subTest(status=status):
                self.provider_request = Mock(
                    return_value=httpx.Response(status)
                )
                with self.assertRaises(ai.GeminiError):
                    self.run_generation()
                self.provider_request.assert_called_once()

    def test_transport_failures_never_retry(self):
        """Connection errors and local read timeouts also stop immediately."""
        for failure in (httpx.ConnectError, httpx.ReadTimeout):
            with self.subTest(failure=failure.__name__):
                self.provider_request = Mock(side_effect=failure('offline'))
                with self.assertRaises(failure):
                    self.run_generation()
                self.provider_request.assert_called_once()

    def test_redirect_cannot_repeat_the_post(self):
        """HTTP redirects cannot resend generation to another endpoint."""
        self.provider_request.side_effect = [
            httpx.Response(307, headers={'Location': '/redirected'}),
            httpx.Response(200, json=provider_body()),
        ]
        with self.assertRaises(ai.GeminiError):
            self.run_generation()
        self.provider_request.assert_called_once()

    def test_continuation_cannot_issue_another_generation(self):
        """A continuation token cannot trigger a hidden follow-up request."""
        body = provider_body('{"title":', 'CONTINUATION')
        body['candidates'][0]['continuationToken'] = 'b2ZmbGluZQ=='
        self.provider_request.side_effect = [
            httpx.Response(200, json=body),
            httpx.Response(200, json=provider_body()),
        ]
        with self.assertRaises(ai.GenerationFailed):
            self.run_generation()
        self.provider_request.assert_called_once()

    def test_truncated_output_is_rejected_without_retry(self):
        """Token exhaustion cannot turn partial JSON into a saved quiz."""
        self.provider_request.return_value = httpx.Response(
            200, json=provider_body('{"title":', 'MAX_TOKENS')
        )
        with self.assertRaises(ai.GenerationFailed):
            self.run_generation()
        self.provider_request.assert_called_once()
