"""Cookie-only JWT authentication with CSRF and session revocation."""

from urllib.parse import urlsplit

from django.conf import settings
from rest_framework.authentication import BaseAuthentication, CSRFCheck
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken


def enforce_csrf(request):
    """Run Django's CSRF checks on DRF's exempt API views."""
    if local_frontend_request(request):
        return
    check = CSRFCheck(lambda request: None)
    check.process_request(request)
    if check.process_view(request, None, (), {}):
        raise PermissionDenied('CSRF verification failed.')


def local_frontend_enabled(request):
    """Confine the optional origin defense to local HTTP development."""
    return (
        settings.LOCAL_FRONTEND_CSRF_COMPATIBILITY
        and settings.DEBUG
        and not settings.JWT_COOKIE_SECURE
        and not settings.CSRF_COOKIE_SECURE
        and request.scheme == 'http'
        and request.get_host().partition(':')[0] in ('localhost', '127.0.0.1')
    )


def local_frontend_request(request):
    """Accept tokenless JSON only from an explicitly trusted loopback UI."""
    origin = request.headers.get('Origin', '')
    return (
        local_frontend_enabled(request)
        and origin in settings.CSRF_TRUSTED_ORIGINS
        and origin in settings.CORS_ALLOWED_ORIGINS
        and urlsplit(origin).hostname in ('localhost', '127.0.0.1')
        and urlsplit(origin).scheme == 'http'
        and settings.CSRF_HEADER_NAME not in request.META
        and (not request.body or request.content_type == 'application/json')
    )


class CsrfOnlyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        """Require CSRF on public write endpoints, including login."""
        enforce_csrf(request)
        return None

    def authenticate_header(self, request):
        """Use a generic challenge for missing or expired sessions."""
        return 'Cookie'


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        """Read cookies and reject access tokens of revoked sessions."""
        raw_token = request.COOKIES.get('access_token')
        if not raw_token:
            return None
        token = self.get_validated_token(raw_token)
        if BlacklistedToken.objects.filter(
            token__jti=token.get('session_jti', '')
        ).exists():
            raise AuthenticationFailed('Session expired. Please log in again.')
        enforce_csrf(request)
        return self.get_user(token), token
