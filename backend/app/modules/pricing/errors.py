"""Safe domain errors for pricing workflows."""


class PricingNotFoundError(Exception):
    pass


class PricingConflictError(Exception):
    pass


class PricingStateError(Exception):
    pass
