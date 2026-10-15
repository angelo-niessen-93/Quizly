"""Authentication regressions covering cookies, revocation and CSRF."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

PASSWORD = 'Correct-Horse-Quizly-928!'


class AuthenticationTests(APITestCase):
    def setup_test(self):
        """Create credentials used by isolated API tests."""
        self.data = dict(
            username='alice',
            email='alice@example.com',
            password=PASSWORD,
            confirmed_password=PASSWORD,
        )
        self.user = get_user_model().objects.create_user(
            username='bob', email='bob@example.com', password=PASSWORD
        )

    setUp = setup_test

    def sign_in(self):
        """Log in through the actual cookie endpoint."""
        return self.client.post(
            '/api/login/', {'username': 'bob', 'password': PASSWORD}
        )

    def test_registration_hashes_password(self):
        """Registration returns no password and stores only its hash."""
        response = self.client.post('/api/register/', self.data)
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username='alice')
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotIn('password', response.data)
        self.assertNotIn('confirmed_password', response.data)

    def test_duplicate_email_case_insensitive(self):
        """An existing email is rejected regardless of capitalization."""
        self.data['email'] = 'BOB@example.com'
        self.assertEqual(
            self.client.post('/api/register/', self.data).status_code, 400
        )

    def test_database_rejects_duplicate_email(self):
        """The database also protects non-API writes."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user(
                username='other', email='BOB@example.com', password=PASSWORD
            )

    def test_duplicate_username(self):
        """Existing usernames cannot be registered again."""
        self.data['username'] = 'bob'
        self.assertEqual(
            self.client.post('/api/register/', self.data).status_code, 400
        )

    def test_invalid_registration(self):
        """Missing, invalid and weak inputs are rejected."""
        cases = [
            {'email': 'bad'},
            {'password': '1', 'confirmed_password': '1'},
            {'confirmed_password': 'different'},
            {'username': ''},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                response = self.client.post(
                    '/api/register/', {**self.data, **changes}
                )
                self.assertEqual(response.status_code, 400)

    @override_settings(JWT_COOKIE_SECURE=True)
    def test_login_cookie_flags(self):
        """Both tokens are secure HTTP-only cookies absent from JSON."""
        response = self.sign_in()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {'detail', 'user'})
        for name in ('access_token', 'refresh_token'):
            cookie = response.cookies[name]
            self.assertTrue(cookie['httponly'])
            self.assertTrue(cookie['secure'])
            self.assertEqual(cookie['samesite'], 'Lax')
            self.assertEqual(cookie['path'], '/api/')

    def test_login_failure_is_generic(self):
        """Unknown and existing accounts receive the same error."""
        responses = [
            self.client.post(
                '/api/login/', {'username': name, 'password': 'wrong'}
            )
            for name in ('bob', 'unknown')
        ]
        self.assertEqual(responses[0].status_code, 401)
        self.assertEqual(responses[0].data, responses[1].data)

    def test_inactive_user_cannot_login(self):
        """Disabled accounts cannot obtain a session."""
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.sign_in().status_code, 401)

    def test_refresh_rotates_and_blacklists(self):
        """An old refresh token is unusable after rotation."""
        self.sign_in()
        old = self.client.cookies['refresh_token'].value
        response = self.client.post('/api/token/refresh/')
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(old, response.cookies['refresh_token'].value)
        self.client.cookies['refresh_token'] = old
        self.assertEqual(
            self.client.post('/api/token/refresh/').status_code, 401
        )

    def test_refresh_does_not_need_access(self):
        """An expired or malformed access cookie cannot block refresh."""
        self.sign_in()
        self.client.cookies['access_token'] = 'expired'
        self.assertEqual(
            self.client.post('/api/token/refresh/').status_code, 200
        )

    def test_logout_revokes_access_and_refresh(self):
        """Stolen copies of both cookies stop working after logout."""
        self.sign_in()
        cookies = self.client.cookies.copy()
        response = self.client.post('/api/logout/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies['access_token']['max-age'], 0)
        self.client.cookies = cookies
        self.assertEqual(self.client.get('/api/quizzes/').status_code, 401)
        self.assertEqual(
            self.client.post('/api/token/refresh/').status_code, 401
        )

    def test_tokens_in_body_are_rejected(self):
        """Refresh exclusively accepts an HTTP-only cookie."""
        self.sign_in()
        token = self.client.cookies['refresh_token'].value
        self.client.cookies.clear()
        self.assertEqual(
            self.client.post(
                '/api/token/refresh/', {'refresh': token}
            ).status_code,
            401,
        )

    def test_csrf_required_on_public_writes(self):
        """Login, registration, refresh and logout require CSRF."""
        client = APIClient(enforce_csrf_checks=True)
        for path in ('login/', 'register/', 'token/refresh/', 'logout/'):
            self.assertEqual(client.post('/api/' + path, {}).status_code, 403)

    def test_csrf_bootstrap_allows_registration(self):
        """A browser can bootstrap CSRF and register."""
        client = APIClient(enforce_csrf_checks=True)
        token = client.get('/api/csrf/').data['csrfToken']
        response = client.post(
            '/api/register/', self.data, HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 201)

    def test_csrf_protects_authenticated_writes(self):
        """Cookie authentication alone cannot authorize a cross-site POST."""
        self.sign_in()
        client = APIClient(enforce_csrf_checks=True)
        client.cookies = self.client.cookies.copy()
        response = client.post('/api/quizzes/', {})
        self.assertEqual(response.status_code, 403)

    def test_real_cookie_session_and_header_rejection(self):
        """Authenticate from cookies and ignore Authorization headers."""
        self.sign_in()
        self.assertEqual(self.client.get('/api/quizzes/').status_code, 200)
        token = self.client.cookies['access_token'].value
        self.client.cookies.clear()
        self.assertEqual(
            self.client.get(
                '/api/quizzes/', HTTP_AUTHORIZATION='Bearer ' + token
            ).status_code,
            401,
        )

    def test_refresh_revokes_old_access(self):
        """Rotation prevents reuse of the prior session's access token."""
        self.sign_in()
        old = self.client.cookies['access_token'].value
        self.client.post('/api/token/refresh/')
        self.client.cookies['access_token'] = old
        self.assertEqual(self.client.get('/api/quizzes/').status_code, 401)

    def test_inactive_user_cannot_refresh(self):
        """Disabling a user also stops existing refresh sessions."""
        self.sign_in()
        self.user.is_active = False
        self.user.save()
        self.assertEqual(
            self.client.post('/api/token/refresh/').status_code, 401
        )
