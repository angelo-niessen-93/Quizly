"""Validate registration and login without exposing credentials."""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirmed_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'confirmed_password']
        read_only_fields = ['id']
        extra_kwargs = {'email': {'required': True, 'allow_blank': False}}

    def validate_email(self, value):
        """Reject duplicate addresses independent of letter case."""
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'Email address already registered.'
            )
        return value

    def validate(self, attrs):
        """Check confirmation and the configured password validators."""
        if attrs['password'] != attrs.pop('confirmed_password'):
            raise serializers.ValidationError(
                {'confirmed_password': 'Passwords do not match.'}
            )
        user = User(username=attrs['username'], email=attrs['email'])
        try:
            validate_password(attrs['password'], user)
        except ValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        return attrs

    def create(self, validated_data):
        """Hash the password before storing the user."""
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        """Use one generic error for unknown users and wrong passwords."""
        user = authenticate(request=self.context['request'], **attrs)
        if user is None:
            raise serializers.ValidationError('Invalid username or password.')
        return {'user': user}
