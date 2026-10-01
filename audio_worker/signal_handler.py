import signal

from common.settings import get_structured_logger

slogger = get_structured_logger()


class SignalHandler:
    def __init__(self):
        self.signal_received = False
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, _frame):
        slogger.info("Received signal {signum}, initiating graceful shutdown...", signum=str(signum))
        self.signal_received = True
