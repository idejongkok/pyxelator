"""Reproducibly compare legacy and structured template matching paths.

This opt-in microbenchmark is intentionally outside ``tests/``. It generates
all inputs locally, checks that both paths select the same target, warms each
path, and reports per-call timing. Run from the repository root:

    python benchmarks/benchmark_matching.py --iterations 20
"""

import argparse
import statistics
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Iterable

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyxelator import find_image_in_screenshot, match_result  # noqa: E402


def build_inputs(directory: Path):
    """Create one deterministic non-ambiguous screenshot/template pair."""
    rng = np.random.default_rng(20261005)
    screenshot = rng.integers(0, 256, size=(180, 320, 3), dtype=np.uint8)
    template = rng.integers(0, 256, size=(24, 36, 3), dtype=np.uint8)
    screenshot[80:104, 140:176] = template

    template_path = directory / "target.png"
    if not cv2.imwrite(str(template_path), template):
        raise RuntimeError("could not write generated benchmark template")
    encoded, buffer = cv2.imencode(".png", screenshot)
    if not encoded:
        raise RuntimeError("could not encode generated benchmark screenshot")
    return buffer.tobytes(), str(template_path)


def samples(call: Callable[[], object], iterations: int) -> Iterable[float]:
    for _ in range(iterations):
        started = time.perf_counter()
        call()
        yield time.perf_counter() - started


def summary(name: str, values) -> None:
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, int(0.95 * len(ordered)))
    print(
        f"{name:12} "
        f"median={statistics.median(ordered) * 1000:8.3f} ms  "
        f"mean={statistics.mean(ordered) * 1000:8.3f} ms  "
        f"p95={ordered[p95_index] * 1000:8.3f} ms"
    )


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=positive_int, default=20)
    parser.add_argument("--warmup", type=positive_int, default=3)
    args = parser.parse_args()

    with TemporaryDirectory() as temporary_directory:
        screenshot, template = build_inputs(Path(temporary_directory))
        legacy = lambda: find_image_in_screenshot(screenshot, template)
        structured = lambda: match_result(screenshot, template)

        legacy_coordinates = legacy()
        structured_result = structured()
        if not structured_result.ok:
            raise RuntimeError(f"structured fixture did not match: {structured_result}")
        if legacy_coordinates != structured_result.coordinates:
            raise RuntimeError(
                "paths selected different targets: "
                f"legacy={legacy_coordinates}, structured={structured_result.coordinates}"
            )

        for _ in range(args.warmup):
            legacy()
            structured()

        legacy_samples = list(samples(legacy, args.iterations))
        structured_samples = list(samples(structured, args.iterations))

    print(f"iterations={args.iterations} warmup={args.warmup} seed=20261005")
    print(f"coordinates={legacy_coordinates}")
    summary("legacy", legacy_samples)
    summary("structured", structured_samples)
    ratio = statistics.median(structured_samples) / statistics.median(legacy_samples)
    print(f"structured/legacy median ratio: {ratio:.2f}x")


if __name__ == "__main__":
    main()
