import json
import logging
from pathlib import Path

import numpy as np
from jiwer import wer
from tqdm import tqdm

from .metrics import TimingAccumulator, compute_wer_pct, normalise_text, token_ops

logger = logging.getLogger(__name__)


def run_engine(adapter, indices, label, *, dataset, wav_write_fn, duration_fn, is_azure=False):
    rows = []
    timing = TimingAccumulator()

    for idx in tqdm(indices, desc=f"{label}", unit="sample"):
        ex = dataset[int(idx)]
        wav_path = wav_write_fn(ex, int(idx))
        ref_raw = ex["text"]
        aud_sec = float(duration_fn(wav_path))

        if is_azure:
            hyp_raw, proc_sec, dbg = adapter.transcribe_with_debug(wav_path)
        else:
            hyp_raw, proc_sec = adapter.transcribe(wav_path)
            dbg = {}

        proc_sec = float(proc_sec)
        timing.add(aud_sec, proc_sec)

        ref_n = normalise_text(ref_raw)
        hyp_n = normalise_text(hyp_raw)

        per_wer = 100.0 * wer([ref_n], [hyp_n])
        ops = token_ops(ref_n, hyp_n)

        row = {
            "engine": label,
            "dataset_index": int(idx),
            "wav_path": wav_path,
            "audio_sec": aud_sec,
            "process_sec": proc_sec,
            "rtf": (proc_sec / aud_sec) if aud_sec else None,
            "wer_pct": float(per_wer),
            "diff_ops": ops,
            "ref_raw": ref_raw,
            "hyp_raw": hyp_raw,
            "ref_norm": ref_n,
            "hyp_norm": hyp_n,
            "engine_debug": dbg,
        }
        rows.append(row)

    overall_wer = compute_wer_pct([r["ref_raw"] for r in rows], [r["hyp_raw"] for r in rows])
    per_wers = [r["wer_pct"] for r in rows]

    summary = {
        "engine": label,
        "num_samples": len(indices),
        "overall_wer_pct": float(overall_wer),
        "rtf": float(timing.rtf),
        "process_sec": float(timing.process_sec),
        "audio_sec": float(timing.audio_sec),
        "per_sample_wer_min": float(np.min(per_wers)) if per_wers else None,
        "per_sample_wer_max": float(np.max(per_wers)) if per_wers else None,
        "per_sample_wer_mean": float(np.mean(per_wers)) if per_wers else None,
    }

    return {"summary": summary, "samples": rows}


def save_results(results: list, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    combined = {
        "summaries": [r["summary"] for r in results],
        "engines": {r["summary"]["engine"]: r["samples"] for r in results}
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    logger.info("Results saved to %s", output_path)
