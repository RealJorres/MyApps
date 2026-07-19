from flask import Flask, request, jsonify, render_template
import requests as req_lib
import json, time, socket, ipaddress
from urllib.parse import urlparse

app = Flask(__name__)

# IP ranges that must never be reachable via the server-side proxy
_BLOCKED = [
    ipaddress.ip_network('127.0.0.0/8'),      # loopback
    ipaddress.ip_network('10.0.0.0/8'),        # private
    ipaddress.ip_network('172.16.0.0/12'),     # private
    ipaddress.ip_network('192.168.0.0/16'),    # private
    ipaddress.ip_network('169.254.0.0/16'),    # link-local / cloud metadata (AWS, GCP, Azure)
    ipaddress.ip_network('0.0.0.0/8'),         # unspecified
    ipaddress.ip_network('100.64.0.0/10'),     # shared address space (RFC 6598)
    ipaddress.ip_network('::1/128'),           # IPv6 loopback
    ipaddress.ip_network('fc00::/7'),          # IPv6 unique local
    ipaddress.ip_network('fe80::/10'),         # IPv6 link-local
]

def _is_ssrf_target(url: str) -> bool:
    """Return True if the URL resolves to a blocked (internal/private) address."""
    try:
        host = urlparse(url).hostname or ''
        if not host:
            return True
        for family, _, _, _, sockaddr in socket.getaddrinfo(host, None):
            try:
                addr = ipaddress.ip_address(sockaddr[0])
                if any(addr in net for net in _BLOCKED):
                    return True
            except ValueError:
                continue
        return False
    except Exception:
        return True  # block on any resolution failure

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/request', methods=['POST'])
def make_request():
    d = request.json if isinstance(request.json, dict) else {}
    url = str(d.get('url') or '').strip()
    method = str(d.get('method') or 'GET').upper()
    headers = d.get('headers') if isinstance(d.get('headers'), dict) else {}
    body = d.get('body') or ''
    if not isinstance(body, str):
        body = str(body)
    try:
        timeout = min(30, max(1, int(d.get('timeout', 10))))
    except (ValueError, TypeError):
        timeout = 10

    if not url:
        return jsonify({'error': 'URL is required'}), 400
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    if _is_ssrf_target(url):
        return jsonify({'error': 'Requests to internal or private addresses are not allowed.'}), 403

    # Strip headers that could be used to override server identity
    safe_headers = {k: v for k, v in headers.items()
                    if k.lower() not in ('host', 'x-forwarded-for', 'x-real-ip')}

    try:
        start = time.time()
        # Do NOT follow redirects: a validated public URL could 3xx to an
        # internal address (e.g. 169.254.169.254), bypassing the SSRF check
        # above. The 3xx status + Location header are surfaced to the caller
        # instead, who can re-issue the request through the same validation.
        kwargs = {'headers': safe_headers, 'timeout': timeout, 'allow_redirects': False}
        if body and method in ('POST', 'PUT', 'PATCH'):
            try:
                json.loads(body)
                kwargs['data'] = body
                if 'content-type' not in {k.lower() for k in safe_headers}:
                    kwargs['headers'] = {**safe_headers, 'Content-Type': 'application/json'}
            except Exception:
                kwargs['data'] = body
        resp = req_lib.request(method, url, **kwargs)
        elapsed = round((time.time() - start) * 1000)
        try:
            resp_body = resp.json()
            resp_type = 'json'
        except Exception:
            resp_body = resp.text
            resp_type = 'text'
        return jsonify({
            'status': resp.status_code,
            'status_text': resp.reason,
            'elapsed_ms': elapsed,
            'headers': dict(resp.headers),
            'body': resp_body,
            'body_type': resp_type,
            'size': len(resp.content),
        })
    except req_lib.exceptions.Timeout:
        return jsonify({'error': f'Request timed out after {timeout}s'}), 408
    except req_lib.exceptions.ConnectionError as e:
        return jsonify({'error': f'Connection error: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5040)
