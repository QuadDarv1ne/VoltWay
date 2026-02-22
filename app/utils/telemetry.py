"""
OpenTelemetry configuration for distributed tracing.

Provides:
- Request tracing across services
- Database query tracing
- HTTP client tracing
- Redis operation tracing
"""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import SpanKind


def setup_opentelemetry(
    service_name: str = "voltway",
    otlp_endpoint: Optional[str] = None,
    enable_console_exporter: bool = True,
) -> Optional[trace.Tracer]:
    """
    Initialize OpenTelemetry for distributed tracing.

    Args:
        service_name: Name of the service for tracing
        otlp_endpoint: OTLP collector endpoint (e.g., http://localhost:4317)
        enable_console_exporter: Enable console exporter for debugging

    Returns:
        Tracer instance or None if initialization fails
    """
    try:
        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": os.getenv("APP_VERSION", "1.0.0"),
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            }
        )

        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)

        # Add exporters
        if enable_console_exporter:
            # Console exporter for debugging
            console_exporter = ConsoleSpanExporter()
            tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )

        # OTLP exporter if endpoint is configured
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )

        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            # App will be passed during startup
        )

        # Instrument HTTPX for external API calls
        HTTPXClientInstrumentor().instrument()

        # Instrument SQLAlchemy for database queries
        SQLAlchemyInstrumentor().instrument()

        # Instrument Redis for cache operations
        RedisInstrumentor().instrument()

        # Get tracer
        tracer = trace.get_tracer(__name__)

        return tracer

    except Exception as e:
        print(f"Failed to initialize OpenTelemetry: {e}")
        return None


def instrument_app(app, tracer_provider=None):
    """
    Instrument a FastAPI application with OpenTelemetry.

    Args:
        app: FastAPI application instance
        tracer_provider: Optional tracer provider (uses global if not provided)
    """
    try:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=tracer_provider,
            excluded_urls="/health,/metrics,/docs,/redoc",
        )
    except Exception as e:
        print(f"Failed to instrument app: {e}")


def shutdown_opentelemetry():
    """Gracefully shutdown OpenTelemetry"""
    try:
        FastAPIInstrumentor.uninstrument()
        tracer_provider = trace.get_tracer_provider()
        tracer_provider.shutdown()
    except Exception as e:
        print(f"Error shutting down OpenTelemetry: {e}")


def get_tracer() -> Optional[trace.Tracer]:
    """Get the global tracer"""
    try:
        return trace.get_tracer(__name__)
    except Exception:
        return None
