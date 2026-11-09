class TranscriptionFailedError(Exception):
    """Exception raised when a transcription fails."""


class NoSpeechDetectedError(TranscriptionFailedError):
    """Raised when no speech is detected before transcription provider submission."""


class MissingAuthTokenError(Exception):
    """Exception raised when an auth token is not provided where required."""
