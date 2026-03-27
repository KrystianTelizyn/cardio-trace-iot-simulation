class HRMonitorException(Exception):
    pass


class MQTTConnectionError(HRMonitorException):
    def __init__(self, exception: Exception):
        self.exception = exception
        super().__init__(f"Failed to connect to MQTT broker: {exception}")


class InvalidConfigurationError(HRMonitorException):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Invalid configuration: {message}")


class SimulatorError(HRMonitorException):
    """Raised when start() is called while a device task failure is recorded.

    Call stop() to tear down and clear the error, then start() again.
    """

    def __init__(self, last_error: Exception):
        self.last_error = last_error
        super().__init__(
            "Simulation is in ERROR state; call stop() before start(). "
            f"Underlying error: {last_error!r}"
        )


class DeviceInitializationError(HRMonitorException):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Device initialization failed: {message}")


class HRVCalculationError(HRMonitorException):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"HRV calculation failed: {message}")


class InvalidPayloadTypeError(HRMonitorException):
    def __init__(self, payload):
        self.payload = payload
        super().__init__(f"Invalid payload type: {type(payload)}")
