class TranscriptionFailedError(Exception):
    """Exception raised when a transcription fails."""


class InteractionFailedError(Exception):
    """Exception raised when a transcription fails."""


class MissingAuthTokenError(Exception):
    """Exception raised when an auth token is not provided where required."""
