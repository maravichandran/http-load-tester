import unittest

from app.load_test_stats import LoadTestStats


class TestLoadTesterStats(unittest.TestCase):
    def test_calculate_results(self):
        load_test_stats = LoadTestStats()
        load_test_stats.results = {'200': [0.1, 0.2, 0.3], '404': [0.4, 0.5], 'error': [0.6]}

        load_test_stats.calculate_stats()

        self.assertEqual(6, load_test_stats.total_requests)
        self.assertEqual(3, load_test_stats.total_errors)
        self.assertAlmostEqual(3 / 6, load_test_stats.error_rate)
        self.assertDictEqual({'200': 3, '404': 2, 'error': 1}, load_test_stats.status_distribution)
        self.assertAlmostEqual(0.35, load_test_stats.mean_latency)
        self.assertAlmostEqual(0.35, load_test_stats.median_latency)
        self.assertAlmostEqual(0.1, load_test_stats.min_latency)
        self.assertAlmostEqual(0.6, load_test_stats.max_latency)
