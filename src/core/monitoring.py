from prometheus_client import start_http_server, Counter, Histogram, Gauge

class Monitoring:
    def __init__(self, port=9090):
        self.port = port
        self.REQUESTS = Counter('api_requests', 'API calls', ['service', 'status'])
        self.ERRORS = Counter('api_errors', 'API errors', ['service', 'type'])
        self.LATENCY = Histogram('request_latency', 'API latency', ['service'])
        self.QUEUE_SIZE = Gauge('task_queue_size', 'Pending tasks in queue')
        
    def start(self):
        start_http_server(self.port)
        
    def track_request(self, service: str, success: bool):
        self.REQUESTS.labels(service, "success" if success else "failure").inc()
        
    def track_error(self, service: str, error_type: str):
        self.ERRORS.labels(service, error_type).inc()
        
    def track_latency(self, service: str, duration: float):
        self.LATENCY.labels(service).observe(duration)
        
    def update_queue_size(self, size: int):
        self.QUEUE_SIZE.set(size) 