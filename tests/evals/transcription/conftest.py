from __future__ import annotations

import numpy as np

from evals.transcription.src.models import AudioSample, DatasetItem, TranscriptionResult


class FakeAdapter:
    def __init__(self, label: str, hyp: str, proc_sec: float = 0.25):
        self.name = label
        self.label = label
        self.hyp = hyp
        self.proc_sec = proc_sec

    def transcribe(self, wav_path: str):  # noqa: ARG002
        return TranscriptionResult(text=self.hyp, duration_sec=self.proc_sec, debug_info={"label": self.label})


class FakeDataset:
    def __init__(self, samples: list[dict]):
        self._samples = [
            DatasetItem(
                audio=AudioSample(
                    array=np.array([0.0, 0.0], dtype=np.float32),
                    sampling_rate=16000,
                    path=s["audio"]["path"],
                ),
                text=s["text"],
            )
            for s in samples
        ]

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, idx: int) -> DatasetItem:
        return self._samples[idx]
