class SimulationServiceException(Exception):
    pass


class InvalidConfigurationError(SimulationServiceException):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Invalid configuration: {message}")
