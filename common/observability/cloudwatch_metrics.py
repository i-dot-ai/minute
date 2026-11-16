"""Emit metrics as Embedded Metric Format (EMF) lines on stdout so CloudWatch picks them up automatically."""

import json
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    name: str
    value: float
    unit: str = "None"


def emit(
    namespace: str, dimensions: dict[str, str], metrics: Sequence[Metric], *, timestamp_ms: int | None = None
) -> None:
    """Write one EMF line describing `metrics` under `namespace`, keyed by `dimensions`."""
    if not metrics:
        return
    payload: dict = {
        "_aws": {
            "Timestamp": timestamp_ms if timestamp_ms is not None else int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": namespace,
                    "Dimensions": [list(dimensions.keys())],
                    "Metrics": [{"Name": metric.name, "Unit": metric.unit} for metric in metrics],
                }
            ],
        },
        **dimensions,
        **{metric.name: metric.value for metric in metrics},
    }
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
