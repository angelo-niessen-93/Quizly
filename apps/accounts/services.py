"""Issue, rotate and revoke cookie-based JWT sessions."""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

LOGOUT_DETAIL = (
    'Log-Out successfully! All Tokens will be deleted. '
    'Refresh token is now invalid.'
)


def save_registration(serializer):
    """Translate concurrent uniqueness conflicts into a safe API error."""
    try:
        with transaction.atomic():
            return serializer.save()
    except IntegrityError:
        raise ValidationError('Username or email address already registered.')


def set_token_cookie(response, name, token, lifetime):
    """Keep JWTs inaccessible to JavaScript and restrict them to the API."""
    response.set_cookie(
        name,
        str(token),
        max_age=int(lifetime.total_seconds()),
        path='/api/',
        secure=settings.JWT_COOKIE_SECURE,
        httponly=True,
        samesite=settings.JWT_COOKIE_SAMESITE,
    )


def session_response(user, payload=None):
    """Create a session whose access token tracks its refresh token."""
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    access['session_jti'] = refresh['jti']
    response = Response(payload or login_payload(user))
    set_token_cookie(response, 'access_token', access, access.lifetime)
    set_token_cookie(response, 'refresh_token', refresh, refresh.lifetime)
    return response


def read_refresh(request):
    """Validate the refresh cookie, never tokens in the request body."""
    try:
        return RefreshToken(request.COOKIES.get('refresh_token', ''))
    except TokenError:
        raise AuthenticationFailed('Session expired. Please log in again.')


@transaction.atomic
def rotate_session(request):
    """Revoke the old session before creating a fresh token pair."""
    refresh = consume_refresh(request)
    user = (
        get_user_model()
        .objects.filter(pk=refresh['user_id'], is_active=True)
        .first()
    )
    if user is None:
        raise AuthenticationFailed('Session expired. Please log in again.')
    return session_response(user, {'detail': 'Token refreshed'})


@transaction.atomic
def revoke_session(request):
    """Revoke the session and remove cookies, even with expired access."""
    if request.COOKIES.get('refresh_token'):
        try:
            consume_refresh(request)
        except AuthenticationFailed:
            pass
    response = Response({'detail': LOGOUT_DETAIL})
    for name in ('access_token', 'refresh_token'):
        set_token_cookie(response, name, '', timedelta(0))
    return response


def login_payload(user):
    """Return the documented login message and public identity fields."""
    return {
        'detail': 'Login successfully!',
        'user': {
            'id': user.pk,
            'username': user.username,
            'email': user.email,
        },
    }


def consume_refresh(request):
    """Serialize refresh use and reject tokens consumed by another request."""
    refresh = read_refresh(request)
    OutstandingToken.objects.select_for_update().get(jti=refresh['jti'])
    try:
        refresh.check_blacklist()
    except TokenError:
        raise AuthenticationFailed('Session expired. Please log in again.')
    refresh.blacklist()
    return refresh
