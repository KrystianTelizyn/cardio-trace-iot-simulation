class RRRepositoryException(Exception): ...


class InitializationError(RRRepositoryException):
    def __init__(self, database_path: str):
        self.database_path = database_path
        super().__init__(f"Failed to initialize repository: {database_path}")


class RecordNotFoundError(RRRepositoryException):
    def __init__(self, tag: str):
        self.tag = tag
        super().__init__(f"Record with tag {tag} not found")


class RecordDuplicateError(RRRepositoryException):
    def __init__(self, tag: str):
        self.tag = tag
        super().__init__(f"Record with tag {tag} already exists")


class RecordValidationError(RRRepositoryException):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
