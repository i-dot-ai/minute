from __future__ import annotations


class FakeAdapter:
    def __init__(self, label: str, hyp: str, proc_sec: float = 0.25, dialogue_entries: list | None = None):
        self.name = label
        self.label = label
        self.hyp = hyp
        self.proc_sec = proc_sec
        self.dialogue_entries = dialogue_entries or []

    def transcribe(self, wav_path: str):  # noqa: ARG002
        return {
            "text": self.hyp,
            "duration_sec": self.proc_sec,
            "dialogue_entries": self.dialogue_entries,
            "debug_info": {"label": self.label},
        }


class FakeDataset:
    def __init__(self, samples: list[dict]):
        self._samples = samples

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, idx: int) -> dict:
        return self._samples[idx]

    @property
    def dataset_version(self) -> str:
        return f"FakeDataset_n{len(self._samples)}"

    @property
    def total_audio_sec(self) -> float:
        return float(len(self._samples))

    @property
    def total_words(self) -> int:
        return sum(len(s.get("text", "").split()) for s in self._samples)
