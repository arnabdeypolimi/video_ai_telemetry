"""Tests for AVSyncTracker."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from avatar_otel.metrics.av_sync import AVSyncTracker


@pytest.fixture
def mock_instruments():
    instruments = MagicMock()
    instruments.av_sync_drift = MagicMock()
    instruments.av_sync_jitter = MagicMock()
    instruments.av_sync_unmatched = MagicMock()
    return instruments


class TestAVSyncTracker:
    def test_basic_drift_measurement(self, mock_instruments):
        tracker = AVSyncTracker(instruments=mock_instruments)
        tracker.audio_captured(chunk_id=1)
        time.sleep(0.01)  # ~10ms
        drift = tracker.frame_rendered(chunk_id=1)

        assert drift is not None
        assert drift > 0
        assert tracker.current_drift_ms == drift
        mock_instruments.av_sync_drift.record.assert_called_once()

    def test_unmatched_chunk_returns_none(self, mock_instruments):
        tracker = AVSyncTracker(instruments=mock_instruments)
        result = tracker.frame_rendered(chunk_id=999)
        assert result is None

    def test_jitter_calculation(self, mock_instruments):
        tracker = AVSyncTracker(instruments=mock_instruments, jitter_window=5)
        # Manually populate drift window with known values
        tracker._drift_window.extend([10.0, 20.0, 30.0, 40.0, 50.0])
        # Mean = 30, MAD = (20+10+0+10+20)/5 = 12
        assert abs(tracker.current_jitter_ms - 12.0) < 0.01

    def test_jitter_with_single_value(self, mock_instruments):
        tracker = AVSyncTracker(instruments=mock_instruments)
        tracker._drift_window.append(10.0)
        assert tracker.current_jitter_ms == 0.0

    def test_warning_callback_on_excessive_drift(self, mock_instruments):
        callback = MagicMock()
        tracker = AVSyncTracker(
            instruments=mock_instruments,
            drift_warning_ms=5.0,
            warning_callback=callback,
        )
        tracker.audio_captured(chunk_id=1)
        time.sleep(0.01)  # >5ms
        tracker.frame_rendered(chunk_id=1)

        callback.assert_called_once()
        call_args = callback.call_args
        assert "drift exceeded" in call_args.args[0].lower()

    def test_no_warning_below_threshold(self, mock_instruments):
        callback = MagicMock()
        tracker = AVSyncTracker(
            instruments=mock_instruments,
            drift_warning_ms=1000.0,
            warning_callback=callback,
        )
        tracker.audio_captured(chunk_id=1)
        tracker.frame_rendered(chunk_id=1)  # nearly instant
        callback.assert_not_called()

    def test_cleanup_expired(self, mock_instruments):
        tracker = AVSyncTracker(
            instruments=mock_instruments,
            chunk_ttl_s=0.01,  # 10ms TTL
        )
        tracker.audio_captured(chunk_id=1)
        tracker.audio_captured(chunk_id=2)
        time.sleep(0.02)  # Wait for expiry

        expired = tracker.cleanup_expired()
        assert expired == 2
        mock_instruments.av_sync_unmatched.add.assert_called_once_with(2)

    def test_cleanup_no_expiry(self, mock_instruments):
        tracker = AVSyncTracker(
            instruments=mock_instruments,
            chunk_ttl_s=100.0,
        )
        tracker.audio_captured(chunk_id=1)
        expired = tracker.cleanup_expired()
        assert expired == 0

    def test_multiple_chunks(self, mock_instruments):
        tracker = AVSyncTracker(instruments=mock_instruments)
        tracker.audio_captured(chunk_id=1)
        tracker.audio_captured(chunk_id=2)
        tracker.audio_captured(chunk_id=3)

        d1 = tracker.frame_rendered(chunk_id=1)
        d3 = tracker.frame_rendered(chunk_id=3)
        d2 = tracker.frame_rendered(chunk_id=2)

        assert d1 is not None
        assert d2 is not None
        assert d3 is not None
        assert mock_instruments.av_sync_drift.record.call_count == 3
