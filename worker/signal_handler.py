import logging
import signal

logger = logging.getLogger(__name__)


class SignalHandler:
    def __init__(self):
        self.signal_received = False
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, _frame):
        logger.info("Received signal %d, initiating graceful shutdown...", signum)
        self.signal_received = True
