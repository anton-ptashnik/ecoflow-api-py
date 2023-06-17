import enum

class OutputCircuit(enum.Enum):
    AC = 1
    DC = 2
    USB = 3

class StateField(enum.Enum):
    CHARGE_LEVEL = 1
    CHARGE_SPEED = 2
    CHARGE_TH_MIN = 3
    CHARGE_TH_MAX = 4
    AC_OUTPUT_IS_ON = 5
    DC_OUTPUT_IS_ON = 6
    USB_OUTPUT_IS_ON = 7
    REMAINING_TIME = 8
    AC_INPUT = 9

class BleConnectionMixin:
    """
    Mixin with connection methods and a connection context manager
    """
    def __init__(self, ble_client) -> None:
        self.device = ble_client

    async def connect(self):
        await self.device.connect()

    async def disconnect(self):
        await self.device.disconnect()

    async def __aenter__(self):
        await self.device.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.device.__aexit__(exc_type, exc_val, exc_tb)
