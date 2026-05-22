# Gunicorn configuration
# Single process with 8 threads — avoids duplicating 127 Flask app instances
# in memory while allowing 8 concurrent requests (up from 4).
# gthread is built into gunicorn (no extra dependency).
#
# Why single worker: loading all 127 sub-apps takes ~512 MB. Two workers
# would need ~1 GB, exceeding Render free tier. Eight threads lets 8 requests
# run concurrently within that single process; only one can hold the GIL at a
# time for CPU-bound work (PDF generation), but I/O-bound requests (most API
# calls, static files) genuinely overlap.

workers     = 1           # 1 OS process — keeps ~512 MB Render free tier happy
worker_class = 'gthread'  # thread-based concurrency within the single process
threads     = 8           # 8 threads = 8 concurrent requests (was 4)
timeout     = 120         # PDF generation (ReportLab) can be slow
graceful_timeout = 30
keepalive   = 5

# Logging
accesslog  = '-'     # stdout
errorlog   = '-'     # stderr
loglevel   = 'info'
