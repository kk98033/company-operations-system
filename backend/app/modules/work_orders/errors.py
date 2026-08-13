"""Domain errors for cases and work orders."""


class WorkOrderNotFoundError(RuntimeError):
    pass


class WorkOrderConflictError(RuntimeError):
    pass


class WorkOrderStateError(RuntimeError):
    pass


class WorkOrderNumberExhaustedError(RuntimeError):
    pass


class QuotationConversionError(RuntimeError):
    pass


class AttachmentValidationError(RuntimeError):
    pass
