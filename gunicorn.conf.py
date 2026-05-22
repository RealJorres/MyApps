# Gunicorn configuration
# Single process with 4 threads — avoids duplicating 128 Flask app instances
# in memory while still allowing 4 concurrent requests.
# gthread is built into gunicorn (no extra dependency).

workers     = 1           # 1 OS process — keeps ~512 MB Render free tier happy
worker_class = 'gthread'  # thread-based concurrency within the single process
threads     = 4           # 4 threads = 4 concurrent requests
timeout     = 120         # PDF generation (ReportLab) can be slow
graceful_timeout = 30
keepalive   = 5

# Logging
accesslog  = '-'     # stdout
errorlog   = '-'     # stderr
loglevel   = 'info'
