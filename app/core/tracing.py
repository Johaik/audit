from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine
import os

def setup_tracing(app: FastAPI, engine: AsyncEngine):
    service_name = os.getenv("OTEL_SERVICE_NAME", "audit-api")
    resource = Resource.create({"service.name": service_name})
    
    provider = TracerProvider(resource=resource)
    
    # Only add exporter if OTEL_EXPORTER_OTLP_ENDPOINT is set
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app, 
        tracer_provider=provider,
        excluded_urls="health" # Don't trace health checks
    )
    
    # Instrument SQLAlchemy
    # Note: SQLAlchemyInstrumentor.instrument() instruments the engine
    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine, # We need the sync engine for instrumentation
        tracer_provider=provider
    )

def get_tracer(name: str):
    return trace.get_tracer(name)
