"""Tests for AdaptiveSampler."""

from __future__ import annotations

import time
from unittest.mock import patch

from avatar_otel.tracing.sampler import AdaptiveSampler


class TestAdaptiveSampler:
    def test_always_trace(self):
        sampler = AdaptiveSampler(window_s=100.0)
        for _ in range(10):
            assert sampler.should_sample("render", always_trace=True)

    def test_anomaly_threshold(self):
        sampler = AdaptiveSampler(window_s=100.0, anomaly_threshold_ms=50.0)
        # First call within window
        sampler.should_sample("render")
        # Anomaly should always pass
        assert sampler.should_sample("render", elapsed_ms=60.0)
        assert not sampler.should_sample("render", elapsed_ms=30.0)

    def test_window_sampling(self):
        sampler = AdaptiveSampler(window_s=0.1)
        # First call should always pass
        assert sampler.should_sample("render")
        # Immediate second call should be rejected
        assert not sampler.should_sample("render")
        # After window passes, should be accepted
        time.sleep(0.15)
        assert sampler.should_sample("render")

    def test_different_stages_independent(self):
        sampler = AdaptiveSampler(window_s=100.0)
        assert sampler.should_sample("render")
        assert sampler.should_sample("encode")
        # Both should be rejected now (within window)
        assert not sampler.should_sample("render")
        assert not sampler.should_sample("encode")

    def test_below_anomaly_threshold_not_sampled(self):
        sampler = AdaptiveSampler(window_s=100.0, anomaly_threshold_ms=50.0)
        sampler.should_sample("render")
        assert not sampler.should_sample("render", elapsed_ms=49.0)
