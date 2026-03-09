from __future__ import annotations

import numpy as np

from evals.transcription.src.models import AMIDatasetSample, AudioSample, TranscriptionResult


class FakeAdapter:
    def __init__(self, label: str, hyp: str, proc_sec: float = 0.25):
        self.name = label
        self.label = label
        self.hyp = hyp
        self.proc_sec = proc_sec

    def transcribe(self, _wav_path: str):
        dialogue_entries = [{"speaker": "Speaker 1", "text": self.hyp, "start_time": 0.0, "end_time": 1.0}]
        return TranscriptionResult(
            text=self.hyp,
            duration_sec=self.proc_sec,
            debug_info={"label": self.label},
            dialogue_entries=dialogue_entries,
        )


class FakeDataset:
    def __init__(self, samples: list[dict]):
        self._samples = []
        for idx, s in enumerate(samples):
            item = AMIDatasetSample(
                audio=AudioSample(
                    array=np.array([0.0, 0.0], dtype=np.float32),
                    sampling_rate=16000,
                    path=s["audio"]["path"],
                ),
                text=s["text"],
                meeting_id="fake_meeting",
                dataset_index=idx,
                duration_sec=1.0,
                num_utterances=1,
                reference_diarization=[{"speaker": "Speaker 1", "text": s["text"], "start_time": 0.0, "end_time": 1.0}],
            )
            self._samples.append(item)

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, idx: int) -> AMIDatasetSample:
        return self._samples[idx]

    @property
    def dataset_version(self) -> str:
        return "FakeDataset_v0"

    @property
    def dataset_split(self) -> str | None:
        return "test"

    @property
    def total_audio_sec(self) -> float:
        return 0.0

    @property
    def total_words(self) -> int:
        return sum(len(s.text.split()) for s in self._samples)
