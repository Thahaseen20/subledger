class DomainError(Exception):
    """Base exception for expected business-rule failures."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class BusinessRuleError(DomainError):
    pass
