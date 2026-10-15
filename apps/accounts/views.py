"""Public authentication endpoints protected against CSRF."""

from django.middleware.csrf import get_token, rotate_token
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .authentication import CsrfOnlyAuthentication
from .serializers import LoginSerializer, RegisterSerializer
from .services import (
    revoke_session,
    rotate_session,
    save_registration,
    session_response,
)


@api_view(['GET'])
@authentication_classes([CsrfOnlyAuthentication])
@permission_classes([AllowAny])
def csrf(request):
    """Bootstrap a CSRF cookie and return the masked header token."""
    return Response({'csrfToken': get_token(request)})


@api_view(['POST'])
@authentication_classes([CsrfOnlyAuthentication])
@permission_classes([AllowAny])
def register(request):
    """Register validated credentials without returning any JWT."""
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    save_registration(serializer)
    return Response({'detail': 'User created successfully!'}, status=201)


@api_view(['POST'])
@authentication_classes([CsrfOnlyAuthentication])
@permission_classes([AllowAny])
def login(request):
    """Authenticate credentials and set both HTTP-only token cookies."""
    serializer = LoginSerializer(
        data=request.data, context={'request': request}
    )
    if not serializer.is_valid():
        raise AuthenticationFailed('Invalid username or password.')
    rotate_token(request)
    return session_response(serializer.validated_data['user'])


@api_view(['POST'])
@authentication_classes([CsrfOnlyAuthentication])
@permission_classes([AllowAny])
def logout(request):
    """Allow logout even after the access token expires."""
    return revoke_session(request)


@api_view(['POST'])
@authentication_classes([CsrfOnlyAuthentication])
@permission_classes([AllowAny])
def token_refresh(request):
    """Rotate tokens using only the refresh cookie."""
    return rotate_session(request)
