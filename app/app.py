import time
import logging
import json
from datetime import datetime, timezone
from flask import Flask, request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# ==========================================
# 1. Prometheus Metrics Configuration
# ==========================================

# Metric: flask_app_requests_total (Counter)
REQUEST_COUNT = Counter(
    'flask_app_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

# Metric: flask_app_request_latency_seconds (Histogram)
REQUEST_LATENCY = Histogram(
    'flask_app_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

# ==========================================
# 2. Structured JSON Logging Configuration
# ==========================================
class JSONFormatter(logging.Formatter):
    def format(self, record):
        # Base JSON fields required by Loki
        log_record = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "message": record.getMessage()
        }
        # Inject contextual request data if present
        if hasattr(record, 'request_context'):
            log_record.update(record.request_context)
        return json.dumps(log_record)

# Initialize standard output logger
logger = logging.getLogger("flask_app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler() 
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.propagate = False # Prevent duplicate text logs from root logger

# ==========================================
# 3. Flask Middleware for Telemetry
# ==========================================
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    # Only track endpoints we care about (ignore 404s for non-existent paths if desired, but we track all here)
    if request.path not in ['/hello', '/metrics']:
        return response

    duration = time.time() - request.start_time

    # Update Prometheus Metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        status_code=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.path
    ).observe(duration)

    # Generate JSON Log Output
    extra_ctx = {
        "endpoint": request.path,
        "method": request.method,
        "status_code": response.status_code,
        "duration": round(duration, 4)
    }
    logger.info("Request processed", extra={"request_context": extra_ctx})

    return response

# ==========================================
# 4. Application Endpoints
# ==========================================
@app.route('/hello', methods=['GET'])
def hello():
    # Supports ?delay=1 parameter to easily trigger latency alerts later[cite: 1]
    delay = request.args.get('delay', type=float, default=0.0)
    if delay > 0:
        time.sleep(delay)
    return {"message": "Hello, Observability!"}, 200

@app.route('/metrics', methods=['GET'])
def metrics():
    # Exposes metrics in Prometheus format[cite: 1]
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)