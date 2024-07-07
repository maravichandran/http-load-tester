import asyncio
import sys
import aiohttp
import argparse
import time
from typing import Tuple, Optional

from app.load_test_stats import LoadTestStats

class HTTPLoadTester:
    """A class for performing HTTP load testing and optionally determining server breaking point."""

    def __init__(self, url: str, qps: Optional[int] = None, verbose: bool = False, retries: int = 5) -> None:
        """
        Initialize the HTTPLoadTester.

        Args:
            url (str): The URL to test.
            qps (Optional[int]): The number of queries per second to perform (if running a single test).
            verbose (bool): Whether to print verbose output.
            retries (int): Number of retry attempts for a failed request.
        """
        self.url: str = url
        self.qps: Optional[int] = qps
        self.verbose: bool = verbose
        self.retries: int = retries
        self.load_test_stats = LoadTestStats()

    async def make_request(self, session: aiohttp.ClientSession) -> None:
        """
        Make a single HTTP request and record the results with retry logic.

        Args:
            session (aiohttp.ClientSession): The session to use for the request.
        """
        start_time: float = time.perf_counter()
        for attempt in range(self.retries):
            try:
                async with session.get(self.url) as response:
                    latency: float = time.perf_counter() - start_time
                    await response.text()
                    self.load_test_stats.results[str(response.status)].append(latency)
                    return
            except Exception as e:
                if attempt < self.retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.load_test_stats.results['error'].append(time.perf_counter() - start_time)
                    self.load_test_stats.error_set.add(str(e))
                    if self.verbose: 
                        print("Error received from request:", str(e))

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
            start_time = time.time()
            end_time = start_time + duration
            interval = 1 / qps
            next_request_time = start_time

            while time.time() < end_time:
                current_time = time.time()
                if current_time >= next_request_time:
                    if current_time < end_time:
                        asyncio.create_task(self.make_request(session))
                        next_request_time += interval
                    await asyncio.sleep(0)  # Yield control to allow other tasks to run
                else:
                    await asyncio.sleep(next_request_time - current_time)

        # Wait for any remaining tasks to complete
        await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})

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

    async def run(self, args: argparse.Namespace) -> None:
        """Run the load test or find the breaking point based on the provided arguments."""
        try:
            if args.find_breaking_point:
                await self.find_breaking_point(args.max_qps, args.duration, args.max_error_rate, args.max_latency)
            else:
                await self.run_test(args.duration)
                self.print_results()
        finally:
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            await asyncio.gather(*tasks, return_exceptions=True)

def parse_arguments():
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="HTTP Load Testing Tool")
    parser.add_argument("--url", default="http://example.com", help="Target URL to test")
    parser.add_argument("--qps", type=int, default=20, help="Queries per second for a single test")
    parser.add_argument("--duration", type=int, default=5, help="Test duration in seconds")
    parser.add_argument("--find-breaking-point", action="store_true", help="Find the breaking point of the server")
    parser.add_argument("--max-qps", type=int, default=1000, help="Maximum queries per second to test when finding breaking point")
    parser.add_argument("--max-error-rate", type=float, default=0.01, help="Maximum acceptable error rate when finding breaking point")
    parser.add_argument("--max-latency", type=float, default=0.5, help="Maximum acceptable mean latency in seconds when finding breaking point")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output including error messages")
    parser.add_argument("--retries", type=int, default=5, help="Number of retry attempts for a failed request")
    return parser.parse_args()

async def main() -> None:
    args = parse_arguments()
    tester = HTTPLoadTester(args.url, args.qps, args.verbose, args.retries)
    await tester.run(args)

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
