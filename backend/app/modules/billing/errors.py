"""Safe billing domain errors."""


class BillingNotFoundError(RuntimeError):
    pass


class BillingConflictError(RuntimeError):
    pass


class BillingStateError(RuntimeError):
    pass
