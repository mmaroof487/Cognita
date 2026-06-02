from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from prometheus_client import Counter, Histogram, Gauge
from fastapi import FastAPI
from app.config import settings

# Initialize Provider
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("axon")

# Prometheus Metrics
axon_agent_runs_total = Counter("axon_agent_runs_total", "Agent Runs", ["tenant_id", "status"])
axon_insights_total = Counter("axon_insights_total", "Insights generated", ["severity", "insight_type"])
axon_agent_cost_usd = Histogram("axon_agent_cost_usd", "Agent Cost in USD")
axon_hitl_pending = Gauge("axon_hitl_pending", "Pending HITL actions", ["tenant_id"])

def instrument_app(app: FastAPI):
    if settings.enable_telemetry:
        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument()
