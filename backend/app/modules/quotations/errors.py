class QuotationNotFoundError(RuntimeError):
    pass


class QuotationConflictError(RuntimeError):
    pass


class QuotationStateError(RuntimeError):
    pass


class QuotationNumberExhaustedError(RuntimeError):
    pass
