import numpy as np


def aggregate_metrics(all_sample_metrics: list[dict]) -> dict[str, dict[str, float]]:
    """
    Calculate mean, std, min, and max statistics for each metric across all samples.
    """
    aggregated: dict[str, dict[str, float]] = {}

    metric_keys = [
        "wer",
        "jaccard_wer",
        "wder",
    ]

    for key in metric_keys:
        values: list[float] = []

        for sample in all_sample_metrics:
            try:
                val = sample.get(key)
                if val is not None and not isinstance(val, dict):
                    values.append(float(val))
            except (KeyError, TypeError, ValueError):
                continue

        if values:
            aggregated[key] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
            }

    return aggregated
