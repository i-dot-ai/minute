import re
from difflib import SequenceMatcher

from jiwer import wer

_unicode_replacements = [
    ("'", "'"),
    ("'", "'"),
    (""", '"'),
    (""", '"'),
    ("–", " "),
    ("—", " "),
    ("…", " "),
]

_non_word = re.compile(r"[^\w\s']+", re.UNICODE)
_ws = re.compile(r"\s+", re.UNICODE)


def normalise_text(s: str) -> str:
    s = (s or "").strip().lower()
    for old, new in _unicode_replacements:
        s = s.replace(old, new)
    s = _non_word.sub(" ", s)
    return _ws.sub(" ", s).strip()


def compute_wer_pct(refs: list[str], hyps: list[str]) -> float:
    return 100.0 * wer([normalise_text(r) for r in refs], [normalise_text(h) for h in hyps])


def token_ops(a: str, b: str) -> dict:
    a = (a or "").split()
    b = (b or "").split()
    sm = SequenceMatcher(a=a, b=b)
    ops = {"equal": 0, "replace": 0, "delete": 0, "insert": 0}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            ops["equal"] += (i2 - i1)
        elif tag == "replace":
            ops["replace"] += max(i2 - i1, j2 - j1)
        elif tag == "delete":
            ops["delete"] += (i2 - i1)
        elif tag == "insert":
            ops["insert"] += (j2 - j1)
    return ops


class TimingAccumulator:
    def __init__(self):
        self.process_sec = 0.0
        self.audio_sec = 0.0

    def add(self, audio_sec: float, process_sec: float):
        self.audio_sec += float(audio_sec)
        self.process_sec += float(process_sec)

    @property
    def rtf(self) -> float:
        return self.process_sec / self.audio_sec if self.audio_sec else float("nan")
