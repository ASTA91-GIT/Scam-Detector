"""
Gunicorn Production Server Configuration for ScamGuard AI
"""

import os
import multiprocessing

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = int(os.getenv("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2, 4)))
threads = int(os.getenv("PYTHON_GETS_THREADS", 2))
worker_class = "gthread"
timeout = 120
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info" if os.getenv("FLASK_ENV") == "production" else "debug"

access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'
