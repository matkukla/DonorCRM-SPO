"""
Authentication views.
"""
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


class LogoutView(APIView):
    """
    POST: Logout by blacklisting the refresh token.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['auth'],
        summary='Logout user',
        description='Logout by blacklisting the refresh token.',
        request=inline_serializer(
            name='LogoutRequest',
            fields={'refresh': serializers.CharField(help_text='Refresh token to blacklist')}
        ),
        responses={
            200: inline_serializer(
                name='LogoutResponse',
                fields={'detail': serializers.CharField()}
            ),
            400: inline_serializer(
                name='LogoutError',
                fields={'detail': serializers.CharField()}
            ),
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {'detail': 'Successfully logged out.'},
                status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {'detail': 'Invalid token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
