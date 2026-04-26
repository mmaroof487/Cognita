"""
OpenTelemetry configuration — skeleton for week 4.
For now, just a no-op tracer that will be filled in during observability week.
"""

from opentelemetry import trace
from app.config import settings


def init_telemetry():
    """Initialize OpenTelemetry (stub for now)."""
    if settings.enable_telemetry:
        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            provider = TracerProvider()
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            trace.set_tracer_provider(provider)
        except Exception as e:
            print(f"Failed to init OTel: {e}")


# Get tracer
tracer = trace.get_tracer(__name__)
