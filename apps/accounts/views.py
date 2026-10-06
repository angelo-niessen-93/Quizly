from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    return Response({'detail': 'Register endpoint prepared.'}, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    return Response({'detail': 'Login endpoint prepared.'}, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    return Response({'detail': 'Logout endpoint prepared.'}, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    return Response({'detail': 'Token refresh endpoint prepared.'}, status=status.HTTP_501_NOT_IMPLEMENTED)
