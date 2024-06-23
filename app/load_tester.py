import asyncio
import sys

import aiohttp
import argparse
import time
from typing import List, Tuple, Optional

from app.load_test_stats import LoadTestStats


class HTTPLoadTester:
    """A class for performing HTTP load testing and optionally determining server breaking point."""

    def __init__(self, url: str, qps: Optional[int] = None) -> None:
        """
        Initialize the HTTPLoadTester.

        Args:
            url (str): The URL to test.
            qps (Optional[int]): The number of queries per second to perform (if running a single test).
        """
        self.url: str = url
        self.qps: Optional[int] = qps
        self.load_test_stats = LoadTestStats()

    async def make_request(self, session: aiohttp.ClientSession) -> None:
        """
        Make a single HTTP request and record the results.

        Args:
            session (aiohttp.ClientSession): The session to use for the request.
        """
        start_time: float = time.perf_counter()
        try:
            async with session.get(self.url) as response:
                await response.text()
                latency: float = time.perf_counter() - start_time
                self.load_test_stats.results[str(response.status)].append(latency)
        except Exception:
            self.load_test_stats.results['error'].append(time.perf_counter() - start_time)

    async def generate_load(self, duration: int, qps: Optional[int] = None) -> None:
        """
        Generate load by making multiple requests per second for a specified duration.

        Args:
            duration (int): The duration of the test in seconds.
            qps (Optional[int]): The number of queries per second to perform. If None, uses self.qps.
        """
        qps = qps or self.qps
        if qps is None:
            raise ValueError("QPS must be specified either in the constructor or as a method argument")

        async with aiohttp.ClientSession() as session:
            end_time = time.time() + duration
            while time.time() < end_time:
                start_time: float = time.time()
                tasks: List[asyncio.Task] = [asyncio.create_task(self.make_request(session)) for _ in range(qps)]
                await asyncio.gather(*tasks)
                elapsed: float = time.time() - start_time
                if elapsed < 1:
                    await asyncio.sleep(1 - elapsed)

    async def run_test(self, duration: int, qps: Optional[int] = None) -> Tuple[float, float]:
        """
        Run a single load test with specified QPS and duration.

        Args:
            duration (int): The duration of the test in seconds.
            qps (Optional[int]): The number of queries per second to perform. If None, uses self.qps.

        Returns:
            Tuple[float, float]: The error rate and mean latency of the test.
        """
        self.load_test_stats = LoadTestStats()
        await self.generate_load(duration, qps or self.qps)  # Use self.qps if qps is None
        self.load_test_stats.calculate_stats()
        return self.load_test_stats.error_rate, self.load_test_stats.mean_latency

    async def find_breaking_point(self, max_qps: int, duration: int, max_error_rate: float, max_latency: float) -> int:
        """
        Find the breaking point of the server using binary search and print the results of the search.

        Args:
            max_qps (int): The maximum QPS to test.
            duration (int): The duration of each test in seconds.
            max_error_rate (float): The maximum acceptable error rate.
            max_latency (float): The maximum acceptable mean latency in seconds.

        Returns:
            int: The maximum QPS the server can handle without exceeding the error rate or latency thresholds.
        """
        low, high = 1, max_qps
        best_qps = 0
        print("Beginning search for breaking point.")

        while low <= high:
            mid = (low + high) // 2
            error_rate, mean_latency = await self.run_test(duration, mid)

            print(f"Tested QPS: {mid}, Error Rate: {error_rate:.2%}, Mean Latency: {mean_latency:.3f}s")

            if error_rate <= max_error_rate and mean_latency <= max_latency:
                best_qps = mid
                low = mid + 1
            else:
                high = mid - 1

        if best_qps == 0:
            print("\nNo acceptable performance level found within the tested range.")
        elif best_qps == max_qps:
            print(
                "\nBreaking point not found within range. The server had adequate performance at all levels of queries per second tested.")
        else:
            print(f"\nBreaking point found: {best_qps} QPS")

        print("\nFinal test results:")
        # Only run the final test if we found a valid QPS
        if best_qps > 0:
            await self.run_test(duration, best_qps)
        self.print_results()
        return best_qps

    def print_results(self) -> None:
        """Print the results of the load test."""
        print(f"Results for {self.url}")
        print(f"Total requests: {self.load_test_stats.total_requests}")
        print(f"Total errors: {self.load_test_stats.total_errors}")
        print(f"Error rate: {self.load_test_stats.error_rate:.3%}")
        print(f"Mean latency: {1000 * self.load_test_stats.mean_latency:.3f} milliseconds")
        print(f"Median latency: {1000 * self.load_test_stats.median_latency:.3f} milliseconds")
        print(f"Min latency: {1000 * self.load_test_stats.min_latency:.3f} milliseconds")
        print(f"Max latency: {1000 * self.load_test_stats.max_latency:.3f} milliseconds")
        print("\nStatus code distribution:")
        for status, count in self.load_test_stats.status_distribution.items():
            print(f"  {status}: {count}")


async def main() -> None:
    """Parse command line arguments and run the load test."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="HTTP Load Testing Tool")
    parser.add_argument("url", help="Target URL to test")
    parser.add_argument("--qps", type=int, default=20, help="Queries per second for a single test")
    parser.add_argument("--duration", type=int, default=5, help="Test duration in seconds")
    parser.add_argument("--find-breaking-point", action="store_true", help="Find the breaking point of the server")
    parser.add_argument("--max-qps", type=int, default=1000,
                        help="Maximum queries per second to test when finding breaking point")
    parser.add_argument("--max-error-rate", type=float, default=0.01,
                        help="Maximum acceptable error rate when finding breaking point")
    parser.add_argument("--max-latency", type=float, default=0.5,
                        help="Maximum acceptable mean latency in seconds when finding breaking point")
    args: argparse.Namespace = parser.parse_args()

    tester: HTTPLoadTester = HTTPLoadTester(args.url, args.qps)

    try:
        if args.find_breaking_point:
            await tester.find_breaking_point(args.max_qps, args.duration, args.max_error_rate,
                                             args.max_latency)
        else:
            await tester.run_test(args.duration)
            tester.print_results()
    finally:
        # Ensure all pending tasks are completed
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        # Set the event loop policy to WindowsSelectorEventLoopPolicy on Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
