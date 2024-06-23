import asynctest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from app.load_test_stats import LoadTestStats
from app.load_tester import HTTPLoadTester


class TestHTTPLoadTester(asynctest.TestCase):
    def setUp(self):
        self.url = "https://example.com"
        self.qps = 10
        self.tester = HTTPLoadTester(self.url, self.qps)

    def test_init(self):
        self.assertEqual(self.tester.url, self.url)
        self.assertEqual(self.tester.qps, self.qps)
        self.assertIsInstance(self.tester.load_test_stats, LoadTestStats)

    @asynctest.patch('aiohttp.ClientSession')
    async def test_make_request_success(self, mock_session):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "Response content"
        mock_session.get.return_value.__aenter__.return_value = mock_response

        await self.tester.make_request(mock_session)

        self.assertEqual(1, len(self.tester.load_test_stats.results['200']))
        self.assertNotIn('error', self.tester.load_test_stats.results)

    @asynctest.patch('aiohttp.ClientSession')
    async def test_make_request_error(self, mock_session):
        mock_session.get.side_effect = Exception("Connection error")

        await self.tester.make_request(mock_session)

        self.assertEqual(1, len(self.tester.load_test_stats.results['error']))

    @asynctest.patch('asyncio.sleep', return_value=None)
    @asynctest.patch('time.time')
    @asynctest.patch('aiohttp.ClientSession')
    @asynctest.patch('app.load_tester.HTTPLoadTester.make_request')
    async def test_generate_load(self, mock_make_request, mock_session, mock_time, mock_sleep):
        mock_time.side_effect = [0, 0.5, 1, 1.5, 2]  # Simulate time passing
        mock_make_request.return_value = None

        await self.tester.generate_load(1)  # Run for 1 second

        self.assertEqual(mock_make_request.call_count, self.qps)

    @asynctest.patch('app.load_tester.HTTPLoadTester.print_results')
    async def test_find_breaking_point(self, mock_print_results):
        max_qps = 100
        duration = 5
        max_error_rate = 0.01
        max_latency = 0.5

        # Expanded list of mock results
        mock_results = [
            (0.005, 0.1),  # Within limits
            (0.008, 0.2),  # Within limits
            (0.01, 0.3),   # At error rate limit
            (0.015, 0.3),  # Above error rate
            (0.008, 0.5),  # At latency limit
            (0.008, 0.6),  # Above latency
            (0.02, 0.7),   # Above both
            (0.005, 0.4),  # Within limits
            (0.009, 0.45), # Within limits
            (0.011, 0.48), # Slightly above error rate
        ]

        self.tester.run_test = AsyncMock(side_effect=mock_results)

        breaking_point = await self.tester.find_breaking_point(max_qps, duration, max_error_rate, max_latency)

        self.assertEqual(91, breaking_point)  # Expected breaking point
        self.assertLessEqual(self.tester.run_test.call_count, len(mock_results))
        mock_print_results.assert_called_once()

        # Expanded list of mock results for the failure case
        mock_results_fail = [
            (0.02, 0.6),   # Above both error rate and latency
            (0.015, 0.55), # Above both
            (0.012, 0.51), # Above both
            (0.011, 0.52), # Above both
            (0.0105, 0.51),# Slightly above both
            (0.0102, 0.505),# Just above both
            (0.011, 0.51), # Above both
            (0.012, 0.52), # Above both
            (0.013, 0.53), # Above both
            (0.014, 0.54), # Above both
        ]

        self.tester.run_test.reset_mock()
        self.tester.run_test.side_effect = mock_results_fail
        mock_print_results.reset_mock()

        breaking_point = await self.tester.find_breaking_point(max_qps, duration, max_error_rate, max_latency)

        self.assertEqual(0, breaking_point)  # Expected breaking point when no acceptable performance is found
        self.assertLessEqual(self.tester.run_test.call_count, len(mock_results_fail))
        mock_print_results.assert_called_once()

    def test_print_results(self):
        self.tester.load_test_stats.total_requests = 100
        self.tester.load_test_stats.total_errors = 5
        self.tester.load_test_stats.error_rate = 0.05
        self.tester.load_test_stats.status_distribution = {'200': 95, '404': 5}
        self.tester.load_test_stats.mean_latency = 0.2
        self.tester.load_test_stats.median_latency = 0.18
        self.tester.load_test_stats.min_latency = 0.1
        self.tester.load_test_stats.max_latency = 0.5

        with patch('builtins.print') as mocked_print:
            self.tester.print_results()
            expected_print_calls = [
                asynctest.mock.call(f"Results for {self.url}"),
                asynctest.mock.call("Total requests: 100"),
                asynctest.mock.call("Total errors: 5"),
                asynctest.mock.call("Error rate: 5.000%"),
                asynctest.mock.call("Mean latency: 200.000 milliseconds"),
                asynctest.mock.call("Median latency: 180.000 milliseconds"),
                asynctest.mock.call("Min latency: 100.000 milliseconds"),
                asynctest.mock.call("Max latency: 500.000 milliseconds"),
                asynctest.mock.call("\nStatus code distribution:"),
                asynctest.mock.call("  200: 95"),
                asynctest.mock.call("  404: 5"),
            ]
            mocked_print.assert_has_calls(expected_print_calls, any_order=False)


if __name__ == '__main__':
    asynctest.main()
