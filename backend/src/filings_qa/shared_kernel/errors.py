"""Errors raised when domain rules are violated."""


class DomainError(Exception):
    """Base class for violations of domain rules."""


class InvalidValueError(DomainError, ValueError):
    """A value object was given data that breaks its invariants."""
