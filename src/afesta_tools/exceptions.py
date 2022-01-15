"""Afesta Tools exceptions."""


class AfestaError(Exception):
    """Base exception."""


class NoCredentialsError(AfestaError):
    """No valid credentials could be found."""


class AuthenticationError(AfestaError):
    """API authentication error."""
