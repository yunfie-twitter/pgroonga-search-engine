from unittest.mock import MagicMock

from src.crawler.anomaly_detector import AnomalyDetector


def test_anomaly_detection_logic():
    # Setup Mock Redis for domain counting tests
    # We mock the redis client inside the detector instance
    detector = AnomalyDetector()
    detector.redis = MagicMock()

    # 1. Test Length Check
    # Assuming MAX_URL_LENGTH is small in test config, or default 256
    # Let's test a ridiculously long URL
    long_url = "https://example.com/" + "a" * 300
    assert detector.is_anomalous(long_url) is True

    # 2. Test Path Repetition (Spider Trap)
    # /cal/cal/cal/cal ...
    trap_url = "https://example.com/calendar/calendar/calendar/calendar"
    assert detector.is_anomalous(trap_url) is True

    normal_url = "https://example.com/blog/2023/01/post"
    assert detector.is_anomalous(normal_url) is False

    # 3. Test Domain Limit
    # Mock redis return value
    detector.redis.get.return_value = "1001" # Over default limit 1000
    assert detector.check_domain_limit("example.com") is True

    detector.redis.get.return_value = "500"
    assert detector.check_domain_limit("example.com") is False
