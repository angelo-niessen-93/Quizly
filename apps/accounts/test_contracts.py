"""Exact authentication contracts supplied from the academy documentation."""

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from .tests import PASSWORD


class AuthenticationContractTests(APITestCase):
    def setup_test(self):
        """Create the identity returned by a real cookie login."""
        self.user = get_user_model().objects.create_user(
            username='bob', email='bob@example.com', password=PASSWORD
        )

    setUp = setup_test

    def sign_in(self):
        """Authenticate using the documented username and password fields."""
        return self.client.post(
            '/api/login/',
            {'username': 'bob', 'password': PASSWORD},
            format='json',
        )

    def test_register_exact_response(self):
        """Registration returns only the documented success message."""
        response = self.client.post(
            '/api/register/', REGISTRATION, format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(), {'detail': 'User created successfully!'}
        )
        self.assertNotIn('access_token', response.cookies)
        self.assertNotIn('refresh_token', response.cookies)

    def test_login_exact_response(self):
        """Login returns the exact success message and user structure."""
        response = self.sign_in()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_login(self.user.pk))
        self.assertIs(type(response.json()['user']['id']), int)

    @override_settings(JWT_COOKIE_SECURE=True)
    def test_refresh_exact_response_and_new_access_cookie(self):
        """Refresh renews the secure access cookie and returns only detail."""
        self.sign_in()
        previous = self.client.cookies['access_token'].value
        response = self.client.post('/api/token/refresh/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'detail': 'Token refreshed'})
        cookie = response.cookies['access_token']
        self.assertNotEqual(cookie.value, previous)
        self.assertTrue(cookie['httponly'])
        self.assertTrue(cookie['secure'])

    def test_logout_exact_response(self):
        """Logout returns the documented punctuation and capitalization."""
        self.sign_in()
        response = self.client.post('/api/logout/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'detail': EXPECTED_LOGOUT})
        for name in ('access_token', 'refresh_token'):
            self.assertEqual(response.cookies[name].value, '')
            self.assertEqual(response.cookies[name]['max-age'], 0)

    def test_invalid_credentials_are_401(self):
        """Wrong, missing and blank login credentials uniformly return 401."""
        for data in (
            {},
            {'username': 'bob'},
            {'username': '', 'password': ''},
            {'username': 'bob', 'password': 'wrong'},
        ):
            with self.subTest(data=data):
                response = self.client.post('/api/login/', data, format='json')
                self.assertEqual(response.status_code, 401)
                self.assertNotIn('access_token', response.cookies)

    def test_missing_authentication_precedes_protected_write_csrf(self):
        """Anonymous protected writes return 401 even without a CSRF token."""
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/quizzes/', {}).status_code, 401)

    def test_invalid_registration_is_400(self):
        """Required registration data cannot be omitted."""
        response = self.client.post('/api/register/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_missing_refresh_is_401(self):
        """The refresh endpoint requires its HTTP-only session cookie."""
        self.assertEqual(
            self.client.post('/api/token/refresh/').status_code, 401
        )

    def browser_post(self, client, path, data=None):
        """Supply the current CSRF token for each browser write."""
        token = client.get('/api/csrf/').json()['csrfToken']
        return client.post(
            path, data or {}, format='json', HTTP_X_CSRFTOKEN=token
        )

    def test_browser_login_refresh_logout_with_csrf(self):
        """The complete cookie session works with real CSRF enforcement."""
        client = APIClient(enforce_csrf_checks=True)
        response = self.browser_post(
            client, '/api/login/', {'username': 'bob', 'password': PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get('/api/quizzes/').status_code, 200)
        response = self.browser_post(client, '/api/token/refresh/')
        self.assertEqual(response.json(), {'detail': 'Token refreshed'})
        response = self.browser_post(client, '/api/logout/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get('/api/quizzes/').status_code, 401)


REGISTRATION = {
    'username': 'alice',
    'email': 'alice@example.com',
    'password': PASSWORD,
    'confirmed_password': PASSWORD,
}
EXPECTED_LOGOUT = (
    'Log-Out successfully! All Tokens will be deleted. '
    'Refresh token is now invalid.'
)


def expected_login(user_id):
    """Provide an independent expected payload for the login contract."""
    return {
        'detail': 'Login successfully!',
        'user': {'id': user_id, 'username': 'bob', 'email': 'bob@example.com'},
    }
