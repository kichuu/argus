"""Telemetry: OpenTelemetry tracer + Phoenix LLM tracing + structlog bridge.

Call setup_telemetry(service_name) once at process startup. Idempotent
(guarded by a module-level flag so accidental double-init is harmless).
"""

from __future__ import annotations

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from argus_core.settings import get_settings

_INITIALIZED: bool = False


def setup_telemetry(service_name: str | None = None) -> None:
    """Initialize OTel tracer + auto-instrumentations.

    Off by default. Set OTEL_ENABLED=true to opt in (requires a reachable
    OTLP collector at OTEL_EXPORTER_OTLP_ENDPOINT). When disabled, no
    auto-instrumentation is registered and the global TracerProvider is
    left untouched — zero risk of blocking on an unreachable collector.

    Safe to call multiple times - second+ calls are no-ops.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return

    settings = get_settings()
    log = structlog.get_logger(__name__)

    if not settings.otel_enabled:
        log.info("telemetry_disabled", service=service_name or settings.otel_service_name)
        _INITIALIZED = True
        return

    name = service_name or settings.otel_service_name

    resource = Resource.create(
        {
            "service.name": name,
            "deployment.environment": settings.app_env,
        }
    )
    provider = TracerProvider(resource=resource)
    if settings.otel_exporter_otlp_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint, insecure=True
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _instrument_fastapi()
    _instrument_sqlalchemy()
    _instrument_httpx()
    _instrument_openai_via_phoenix(settings.phoenix_collector_endpoint, name)
    _bridge_structlog_to_traces()

    log.info("telemetry_enabled", service=name, exporter=settings.otel_exporter_otlp_endpoint)
    _INITIALIZED = True


def _instrument_fastapi() -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor().instrument()
    except Exception as exc:
        structlog.get_logger(__name__).warning(
            "fastapi instrumentation skipped", error=str(exc)
        )


def _instrument_sqlalchemy() -> None:
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument()
    except Exception as exc:
        structlog.get_logger(__name__).warning(
            "sqlalchemy instrumentation skipped", error=str(exc)
        )


def _instrument_httpx() -> None:
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception as exc:
        structlog.get_logger(__name__).warning(
            "httpx instrumentation skipped", error=str(exc)
        )


def _instrument_openai_via_phoenix(endpoint: str, service_name: str) -> None:
    """OpenInference wires LLM-call spans onto the global OTel tracer.

    We deliberately do NOT call phoenix.otel.register(): it overrides our
    BatchSpanProcessor with a SimpleSpanProcessor pointing at the Phoenix
    collector, which blocks every span export for ~30s when Phoenix isn't
    running — and that turns out to deadlock the orchestrator since DB +
    HTTP spans propagate through the same processor. Stick with the global
    BatchSpanProcessor + OTLP exporter; Phoenix can subscribe to those
    when the user actually starts it.
    """
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor

        OpenAIInstrumentor().instrument(skip_dep_check=True)
        del endpoint, service_name  # kept in signature for API stability
    except Exception as exc:
        structlog.get_logger(__name__).warning(
            "openai instrumentation skipped", error=str(exc)
        )


def _bridge_structlog_to_traces() -> None:
    """Trace-context injection lives in argus_core.logging._add_trace_context.

    That processor is wired unconditionally into the structlog chain by
    configure_logging(); it lazy-imports opentelemetry and no-ops when no
    span is active. Nothing to do here at runtime - this function exists as
    a documented hook in case future bridges (e.g. log -> span events) are
    added without changing setup_telemetry's call sites.
    """
    return None


def get_tracer(name: str = "argus") -> trace.Tracer:
    return trace.get_tracer(name)
