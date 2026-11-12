class TranscriptionFailedError(Exception):
    """Exception raised when a transcription fails."""


class NoSpeechDetectedError(Exception):
    """Signals an empty provider response with no speech detected in the audio."""


class MissingAuthTokenError(Exception):
    """Exception raised when an auth token is not provided where required."""
