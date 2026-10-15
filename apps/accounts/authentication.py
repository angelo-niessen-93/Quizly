"""Cookie-only JWT authentication with CSRF and session revocation."""

from rest_framework.authentication import BaseAuthentication, CSRFCheck
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken


def enforce_csrf(request):
    """Run Django's CSRF checks on DRF's exempt API views."""
    check = CSRFCheck(lambda request: None)
    check.process_request(request)
    if check.process_view(request, None, (), {}):
        raise PermissionDenied('CSRF verification failed.')


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
        enforce_csrf(request)
        raw_token = request.COOKIES.get('access_token')
        if not raw_token:
            return None
        token = self.get_validated_token(raw_token)
        if BlacklistedToken.objects.filter(
            token__jti=token.get('session_jti', '')
        ).exists():
            raise AuthenticationFailed('Session expired. Please log in again.')
        return self.get_user(token), token
