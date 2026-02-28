"""Tests for PyTorch auto-instrumentation — uses mocked torch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from avatar_otel.instrumentation.pytorch import (
    instrument_pytorch,
    uninstrument_pytorch,
)


class MockParameter:
    def __init__(self, device="cpu"):
        self._device = device

    @property
    def device(self):
        return self._device


class MockModule:
    """Simulates torch.nn.Module behavior."""

    def __init__(self):
        self._parameters = [MockParameter("cpu")]

    def __call__(self, *args, **kwargs):
        return "output"

    def parameters(self):
        return self._parameters


class TestPyTorchInstrumentation:
    def setup_method(self):
        uninstrument_pytorch()

    def teardown_method(self):
        uninstrument_pytorch()

    def test_instrument_without_torch(self):
        with patch.dict("sys.modules", {"torch": None}):
            result = instrument_pytorch()
        assert result is False

    def test_instrument_with_mock_torch(self):
        mock_torch = MagicMock()
        mock_torch.nn.Module.__call__ = MockModule.__call__
        mock_torch.cuda.is_available.return_value = False

        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = instrument_pytorch()
        assert result is True

    def test_uninstrument_restores_original(self):
        mock_torch = MagicMock()
        original_call = mock_torch.nn.Module.__call__
        mock_torch.cuda.is_available.return_value = False

        with patch.dict("sys.modules", {"torch": mock_torch}):
            instrument_pytorch()
            uninstrument_pytorch()

        assert mock_torch.nn.Module.__call__ == original_call

    def test_uninstrument_noop_when_not_instrumented(self):
        uninstrument_pytorch()  # Should not raise

    def test_double_instrument_is_noop(self):
        mock_torch = MagicMock()
        mock_torch.nn.Module.__call__ = MockModule.__call__
        mock_torch.cuda.is_available.return_value = False

        with patch.dict("sys.modules", {"torch": mock_torch}):
            assert instrument_pytorch() is True
            assert instrument_pytorch() is True  # second call is noop

    def test_aggregator_receives_timing(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.Tensor = type("Tensor", (), {})

        mock_aggregator = MagicMock()

        # Create a real callable module
        class FakeModule:
            __class__ = type("TestModel", (), {"__name__": "TestModel"})

            def __call__(self, *args, **kwargs):
                return "result"

            def parameters(self):
                return []

        fake_module = FakeModule()
        original_call = FakeModule.__call__

        mock_torch.nn.Module.__call__ = original_call

        with patch.dict("sys.modules", {"torch": mock_torch}):
            instrument_pytorch(
                sample_rate=0.0,  # No spans
                aggregator=mock_aggregator,
            )

            from avatar_otel.instrumentation import pytorch

            pytorch._original_module_call = original_call

            # Simulate instrumented call
            pytorch._instrumented_call(fake_module, "input")

        mock_aggregator.record.assert_called_once()
        call_kwargs = mock_aggregator.record.call_args[1]
        assert "forward_pass_ms" in call_kwargs
        assert call_kwargs["forward_pass_ms"] >= 0
