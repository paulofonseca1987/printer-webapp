# Gunicorn configuration file
# Run with: gunicorn -c gunicorn.conf.py app:app

import multiprocessing

# Bind to all interfaces on port 5000
bind = "0.0.0.0:5000"

# Number of worker processes
# Using 1 worker because the print queue is in-memory and not shared between workers
workers = 1

# Worker class - sync is fine for this simple app
worker_class = "sync"

# Timeout for worker processes (seconds)
timeout = 30

# Graceful timeout (seconds to finish requests before force kill)
graceful_timeout = 10

# Maximum requests per worker before restart (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Process naming
proc_name = "printer-webapp"

# Don't preload - let each worker start its own print queue thread
preload_app = False
