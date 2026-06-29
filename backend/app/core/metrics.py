import threading
import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager


LabelSet = tuple[tuple[str, str], ...]


def _labels(**labels: str | int | None) -> LabelSet:
    return tuple(sorted((key, str(value)) for key, value in labels.items() if value is not None))


def _format_labels(labels: LabelSet) -> str:
    if not labels:
        return ""
    encoded = ",".join(f'{key}="{value}"' for key, value in labels)
    return f"{{{encoded}}}"


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: defaultdict[tuple[str, LabelSet], float] = defaultdict(float)
        self._summaries: defaultdict[tuple[str, LabelSet], list[float]] = defaultdict(lambda: [0.0, 0.0])

    def increment(self, name: str, amount: float = 1.0, **labels: str | int | None) -> None:
        with self._lock:
            self._counters[(name, _labels(**labels))] += amount

    def observe(self, name: str, value: float, **labels: str | int | None) -> None:
        with self._lock:
            summary = self._summaries[(name, _labels(**labels))]
            summary[0] += 1
            summary[1] += value

    @contextmanager
    def timer(self, name: str, **labels: str | int | None) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.observe(name, time.perf_counter() - start, **labels)

    def render_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            counters = sorted(self._counters.items())
            summaries = sorted(self._summaries.items())

        for (name, labels), value in counters:
            lines.append(f"{name}_total{_format_labels(labels)} {value:g}")
        for (name, labels), (count, total) in summaries:
            label_text = _format_labels(labels)
            lines.append(f"{name}_seconds_count{label_text} {count:g}")
            lines.append(f"{name}_seconds_sum{label_text} {total:g}")
        return "\n".join(lines) + "\n"

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            counters = dict(self._counters)
            summaries = dict(self._summaries)
        values: dict[str, float] = {}
        for (name, labels), value in counters.items():
            label_suffix = ".".join(f"{key}:{label_value}" for key, label_value in labels)
            values[f"{name}{'.' + label_suffix if label_suffix else ''}.total"] = value
        for (name, labels), (count, total) in summaries.items():
            label_suffix = ".".join(f"{key}:{label_value}" for key, label_value in labels)
            prefix = f"{name}{'.' + label_suffix if label_suffix else ''}"
            values[f"{prefix}.seconds_count"] = count
            values[f"{prefix}.seconds_sum"] = total
        return values

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._summaries.clear()


metrics = MetricsRegistry()
