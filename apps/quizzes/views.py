from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET', 'POST'])
def quiz_list_create(request):
    return Response({'detail': 'Quiz list/create endpoint prepared.'}, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(['GET', 'PATCH', 'DELETE'])
def quiz_detail(request, pk):
    return Response({'detail': 'Quiz detail endpoint prepared.'}, status=status.HTTP_501_NOT_IMPLEMENTED)
