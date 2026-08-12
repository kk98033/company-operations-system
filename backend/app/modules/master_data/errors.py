class MasterNotFoundError(RuntimeError):
    pass


class MasterConflictError(RuntimeError):
    pass


class MasterDuplicateError(RuntimeError):
    pass
