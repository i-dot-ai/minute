import logging

import numpy as np
from tqdm import tqdm

logger = logging.getLogger(__name__)


def select_longest_samples(dataset, num_samples: int = 10):
    durations = []

    for idx, ex in tqdm(enumerate(dataset), desc="Analyzing audio durations", total=len(dataset), unit="sample"):
        audio = ex["audio"]
        dur_sec = len(audio["array"]) / audio["sampling_rate"]
        durations.append((idx, dur_sec))

    durations_sorted = sorted(durations, key=lambda x: x[1], reverse=True)
    selected = durations_sorted[:num_samples]

    indices = [idx for idx, _ in selected]
    lengths = [dur for _, dur in selected]

    stats = {
        "count": len(lengths),
        "total_sec": float(np.sum(lengths)),
        "min_sec": float(np.min(lengths)),
        "max_sec": float(np.max(lengths)),
        "mean_sec": float(np.mean(lengths)),
        "samples": [{"index": idx, "duration_sec": dur} for idx, dur in selected]
    }

    return indices, stats
