# Gunicorn configuration for production deployment

bind = "0.0.0.0:5000"
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2
preload_app = True
max_requests = 1000
max_requests_jitter = 100

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "generation-service"

# Server mechanics
daemon = False
pidfile = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Generation Service")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Generation Service is ready. Listening on %s", bind)

def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    # Start background services only in the first worker
    if worker.age == 0 and hasattr(server, '_background_services_started'):
        return
    
    import os
    if os.environ.get('ENABLE_BACKGROUND_SERVICES', 'false').lower() == 'true':
        try:
            from app import start_background_services
            start_background_services()
            server.log.info("Background services started in worker %s", worker.pid)
            server._background_services_started = True
        except Exception as e:
            server.log.error("Failed to start background services: %s", e)

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")