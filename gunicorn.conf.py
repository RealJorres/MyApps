# Gunicorn configuration
# Single process with 8 threads — sub-apps are now lazy-loaded on first
# request (LazyDispatcher), so startup RAM is near zero and only apps that
# are actually visited consume memory.  A second worker would duplicate that
# growing footprint for no benefit on a single-core free-tier dyno.
# gthread is built into gunicorn (no extra dependency).
#
# Why single worker: Render free tier is 512 MB / single vCPU. With lazy
# loading, the 135 sub-apps are imported on demand rather than all at once,
# so steady-state memory is proportional to traffic mix, not app count.
# Eight threads let 8 requests run concurrently within that one process;
# only one holds the GIL at a time for CPU-bound work (PDF generation), but
# I/O-bound requests (most API calls, static files) genuinely overlap.

workers     = 1           # 1 OS process — lazy loading keeps RAM proportional to traffic
worker_class = 'gthread'  # thread-based concurrency within the single process
threads     = 8           # 8 threads = 8 concurrent requests (was 4)
timeout     = 120         # PDF generation (ReportLab) can be slow
graceful_timeout = 30
keepalive   = 5

# Logging
accesslog  = '-'     # stdout
errorlog   = '-'     # stderr
loglevel   = 'info'
