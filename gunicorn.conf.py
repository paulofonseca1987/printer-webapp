# Gunicorn configuration file
# Run with: gunicorn -c gunicorn.conf.py app:app

import multiprocessing

# Bind to all interfaces on port 5000
bind = "0.0.0.0:5000"

# Number of worker processes
# For I/O bound apps like this, 2-4 workers per core is reasonable
# But since we have a single print queue, using fewer workers is safer
workers = 2

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

# Preload app for faster worker startup
preload_app = True
