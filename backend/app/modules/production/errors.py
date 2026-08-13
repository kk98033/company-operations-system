"""Safe domain error markers for production operations."""


class ProductionNotFoundError(RuntimeError):
    pass


class ProductionStateError(RuntimeError):
    pass


class ProductionConflictError(RuntimeError):
    pass


class InventoryInsufficientError(RuntimeError):
    pass
