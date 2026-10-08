class TranscriptionFailedError(Exception):
    """Exception raised when a transcription fails."""


class TranscriptionAlreadyStartedError(Exception):
    """A duplicate ready message arrived after transcription had already started."""


class StaleTranscriptionRunError(Exception):
    """A queued message belongs to an older transcription run."""


class InteractionFailedError(Exception):
    """Exception raised when a transcription fails."""


class MissingAuthTokenError(Exception):
    """Exception raised when an auth token is not provided where required."""
