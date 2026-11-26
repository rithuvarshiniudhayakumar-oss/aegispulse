import pytest

from intelligence.anomaly_detection import build_default_detector


@pytest.fixture(scope="session")
def detector():
    return build_default_detector()
