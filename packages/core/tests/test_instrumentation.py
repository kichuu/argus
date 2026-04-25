from __future__ import annotations

import structlog
from argus_core import instrumentation
from argus_core.instrumentation import get_tracer, setup_telemetry
from argus_core.logging import _add_trace_context, configure_logging
from argus_core.settings import get_settings


def _reset_init_flag() -> None:
    instrumentation._INITIALIZED = False


def test_setup_telemetry_idempotent() -> None:
    _reset_init_flag()
    setup_telemetry("argus-test")
    setup_telemetry("argus-test")
    assert instrumentation._INITIALIZED is True


def test_setup_telemetry_with_no_endpoint(monkeypatch) -> None:
    _reset_init_flag()
    settings = get_settings()
    monkeypatch.setattr(settings, "otel_exporter_otlp_endpoint", "")
    setup_telemetry("argus-test-noendpoint")
    assert instrumentation._INITIALIZED is True


def test_log_record_carries_trace_id(monkeypatch) -> None:
    _reset_init_flag()
    settings = get_settings()
    monkeypatch.setattr(settings, "otel_enabled", True)
    monkeypatch.setattr(settings, "otel_exporter_otlp_endpoint", "")
    configure_logging()
    setup_telemetry("argus-test-trace")
    tracer = get_tracer("argus-test")

    with (
        structlog.testing.capture_logs(processors=[_add_trace_context]) as captured,
        tracer.start_as_current_span("test-span"),
    ):
        structlog.get_logger("test").info("hello")

    assert captured, "expected at least one captured log entry"
    event = captured[0]
    assert "trace_id" in event
    assert "span_id" in event
    assert len(event["trace_id"]) == 32
    assert len(event["span_id"]) == 16
