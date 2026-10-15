"""Original-frontend compatibility and fail-closed CSRF regressions."""

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from .test_contracts import REGISTRATION
from .tests import PASSWORD

ORIGIN = 'http://127.0.0.1:5500'


@override_settings(
    LOCAL_FRONTEND_CSRF_COMPATIBILITY=True,
    DEBUG=True,
    JWT_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    CORS_ALLOWED_ORIGINS=[ORIGIN, 'http://localhost:5500'],
    CSRF_TRUSTED_ORIGINS=[ORIGIN, 'http://localhost:5500'],
)
class LocalFrontendCsrfTests(APITestCase):
    def setup_test(self):
        """Enforce real CSRF checks and use the original frontend's headers."""
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.defaults = {'HTTP_HOST': '127.0.0.1:8000'}
        self.headers = {'HTTP_ORIGIN': ORIGIN}
        get_user_model().objects.create_user(
            username='bob', email='bob@example.com', password=PASSWORD
        )

    setUp = setup_test

    def register(self, **headers):
        """Send a registration without a CSRF bootstrap or token header."""
        return self.client.post(
            '/api/register/', REGISTRATION, format='json', **headers
        )

    def login(self):
        """Sign in with the unmodified upstream JSON request contract."""
        return self.client.post(
            '/api/login/',
            {'username': 'bob', 'password': PASSWORD},
            format='json',
            **self.headers,
        )

    def test_original_registration(self):
        """Unauthenticated registration works from each local UI origin."""
        for origin in (ORIGIN, 'http://localhost:5500'):
            with self.subTest(origin=origin):
                response = self.register(HTTP_ORIGIN=origin)
                self.assertEqual(response.status_code, 201)
                get_user_model().objects.filter(username='alice').delete()

    def test_original_cookie_session(self):
        """Login, tokenless refresh and logout preserve session security."""
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.client.get('/api/quizzes/').status_code, 200)
        old = self.client.cookies.copy()
        response = self.client.post('/api/token/refresh/', **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(
            old['refresh_token'], response.cookies['refresh_token']
        )
        self.logout_and_check()
        self.client.cookies = old
        self.assertEqual(self.client.get('/api/quizzes/').status_code, 401)

    def logout_and_check(self):
        """Log out and confirm the browser loses authenticated access."""
        response = self.client.post('/api/logout/', **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/quizzes/').status_code, 401)

    def test_original_authenticated_write(self):
        """Trusted JSON reaches quiz validation; untrusted writes fail CSRF."""
        self.login()
        response = self.client.post(
            '/api/quizzes/', {}, format='json', **self.headers
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/quizzes/', {}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_untrusted_origins(self):
        """Missing, opaque, foreign and misleading loopback origins fail."""
        for origin in (
            '',
            'null',
            'https://evil.test',
            'http://127.0.0.1:5501',
            'http://127.0.0.1.evil.test:5500',
            ORIGIN + '.evil.test',
        ):
            with self.subTest(origin=origin):
                self.assertEqual(
                    self.register(HTTP_ORIGIN=origin).status_code, 403
                )

    def test_both_allowlists_required(self):
        """CORS alone or CSRF trust alone cannot authorize tokenless writes."""
        for name in ('CORS_ALLOWED_ORIGINS', 'CSRF_TRUSTED_ORIGINS'):
            with self.subTest(setting=name), override_settings(**{name: []}):
                self.assertEqual(
                    self.register(**self.headers).status_code, 403
                )

    def test_production_guards(self):
        """No tokenless fallback exists with production security settings."""
        cases = (
            {'DEBUG': False},
            {'JWT_COOKIE_SECURE': True},
            {'CSRF_COOKIE_SECURE': True},
            {'LOCAL_FRONTEND_CSRF_COMPATIBILITY': False},
        )
        for settings in cases:
            with override_settings(**settings):
                self.assertEqual(
                    self.register(**self.headers).status_code, 403
                )

    def test_remote_api_rejected(self):
        """The origin defense cannot apply to remote API hosts."""
        with override_settings(ALLOWED_HOSTS=['api.example.com', '127.0.0.1']):
            self.assertEqual(
                self.register(
                    HTTP_ORIGIN=ORIGIN, HTTP_HOST='api.example.com'
                ).status_code,
                403,
            )

    def test_https_rejected(self):
        """HTTPS always requires the standard CSRF token."""
        response = self.client.post(
            '/api/register/',
            REGISTRATION,
            format='json',
            secure=True,
            **self.headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_form_content_types_rejected(self):
        """HTML forms and text/plain cannot use the JSON compatibility path."""
        for content_type in (
            'application/x-www-form-urlencoded',
            'text/plain',
            'multipart/form-data; boundary=test',
        ):
            response = self.client.post(
                '/api/register/',
                'username=alice',
                content_type=content_type,
                **self.headers,
            )
            self.assertEqual(response.status_code, 403)

    def test_invalid_supplied_token_rejected(self):
        """Compatibility never hides an invalid or empty CSRF header."""
        self.client.get('/api/csrf/')
        for token in ('invalid', ''):
            response = self.register(HTTP_X_CSRFTOKEN=token, **self.headers)
            self.assertEqual(response.status_code, 403)

    def test_wsgi_empty_refresh(self):
        """WSGI defaults absent Content-Type to text/plain on empty refresh."""
        self.login()
        response = self.client.post(
            '/api/token/refresh/',
            '',
            content_type='text/plain',
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)

    def test_token_flow_still_works(self):
        """Standard CSRF clients continue to use Django's token validation."""
        token = self.client.get('/api/csrf/').json()['csrfToken']
        response = self.register(HTTP_X_CSRFTOKEN=token, **self.headers)
        self.assertEqual(response.status_code, 201)

    def test_admin_keeps_csrf(self):
        """The compatibility option never exempts Django's admin views."""
        response = self.client.post('/admin/login/', {}, **self.headers)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_quiz_stays_protected(self):
        """A trusted Origin is not an authentication credential."""
        response = self.client.post(
            '/api/quizzes/', {}, format='json', **self.headers
        )
        self.assertEqual(response.status_code, 401)
