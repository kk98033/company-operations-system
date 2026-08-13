"""Safe shipment domain errors."""


class ShipmentNotFoundError(Exception):
    pass


class ShipmentConflictError(Exception):
    pass


class ShipmentInventoryError(Exception):
    pass


class ShipmentStateError(Exception):
    pass


class ShipmentCompletionPermissionError(Exception):
    pass
