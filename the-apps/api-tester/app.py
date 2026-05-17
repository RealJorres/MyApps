from flask import Flask, request, jsonify, render_template
import requests as req_lib
import json, time

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/request', methods=['POST'])
def make_request():
    d = request.json or {}
    url = d.get('url', '').strip()
    method = d.get('method', 'GET').upper()
    headers = d.get('headers', {})
    body = d.get('body', '')
    timeout = min(30, max(1, int(d.get('timeout', 10))))
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        start = time.time()
        kwargs = {'headers': headers, 'timeout': timeout, 'allow_redirects': True}
        if body and method in ('POST', 'PUT', 'PATCH'):
            try:
                json.loads(body)
                kwargs['data'] = body
                if 'content-type' not in {k.lower() for k in headers}:
                    kwargs['headers'] = {**headers, 'Content-Type': 'application/json'}
            except:
                kwargs['data'] = body
        resp = req_lib.request(method, url, **kwargs)
        elapsed = round((time.time() - start) * 1000)
        try:
            resp_body = resp.json()
            resp_type = 'json'
        except:
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
