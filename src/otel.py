import logging
import os

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.urllib import URLLibInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import format_span_id, format_trace_id, get_current_span


def _otlp_endpoint() -> str:
    return os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")


def _configure_pyroscope():
    address = os.getenv("PYROSCOPE_SERVER_ADDRESS")
    if not address:
        return
    try:
        import pyroscope  # type: ignore
    except Exception:
        logging.getLogger(__name__).warning("Pyroscope not installed; profiling disabled")
        return

    app_name = os.getenv("PYROSCOPE_APP_NAME", "books-api")
    try:
        pyroscope.configure(
            application_name=app_name,
            server_address=address,
            tags={"service_name": app_name},
        )
    except Exception as exc:
        logging.getLogger(__name__).warning("Pyroscope profiling disabled: %s", exc)


def _log_hook(logger, log_record):
    span = get_current_span()
    context = span.get_span_context() if span else None
    if context and context.is_valid:
        log_record.attributes["trace_id"] = format_trace_id(context.trace_id)
        log_record.attributes["span_id"] = format_span_id(context.span_id)


def configure_otel(app):
    os.environ.setdefault("OTEL_PYTHON_EXPERIMENTAL_ENABLE_METRICS_EXPORTER", "true")
    os.environ.setdefault("OTEL_LOGS_EXPORTER", "otlp")
    _configure_pyroscope()
    service_name = os.getenv("OTEL_SERVICE_NAME", "books-api")
    resource = Resource.create({"service.name": service_name})

    span_exporter = OTLPSpanExporter(endpoint=f"{_otlp_endpoint()}/v1/traces")
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{_otlp_endpoint()}/v1/metrics"),
        export_interval_millis=15000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    log_exporter = OTLPLogExporter(endpoint=f"{_otlp_endpoint()}/v1/logs")
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)

    LoggingInstrumentor().instrument(set_logging_format=True, log_hook=_log_hook)
    HTTPXClientInstrumentor().instrument()
    URLLibInstrumentor().instrument()

    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
