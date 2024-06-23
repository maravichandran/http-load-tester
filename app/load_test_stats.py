from statistics import mean, median
from typing import Dict, List
from collections import defaultdict


class LoadTestStats:
    """A class to hold and calculate statistics for the load tester."""

    def __init__(self):
        self.results: Dict[str, List[float]] = defaultdict(list)
        self.total_requests: int = 0
        self.total_errors: int = 0
        self.error_rate: float = 0.0
        self.status_distribution: Dict[str, int] = {}
        self.mean_latency = -1
        self.median_latency = -1
        self.min_latency = -1
        self.max_latency = -1

    def add_result(self, status: str, latency: float) -> None:
        """Add a single result to the stats."""
        self.results[status].append(latency)

    def calculate_stats(self) -> None:
        """Calculate all statistics based on the collected results."""
        all_latencies: List[float] = []
        self.total_errors = 0
        for status, latencies in self.results.items():
            all_latencies.extend(latencies)
            if status.startswith('4') or status.startswith('5') or status == 'error':
                self.total_errors += len(latencies)

        self.total_requests = len(all_latencies)
        self.error_rate = self.total_errors / self.total_requests if self.total_requests > 0 else 0
        self.status_distribution = {status: len(latencies) for status, latencies in self.results.items()}

        if all_latencies:
            self.mean_latency = mean(all_latencies)
            self.median_latency = median(all_latencies)
            self.min_latency = min(all_latencies)
            self.max_latency = max(all_latencies)
