from flask import Flask, request, jsonify, render_template
import ssl, socket
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check', methods=['POST'])
def check():
    d = request.json or {}
    domain = d.get('domain', '').strip().lower()
    if not domain: return jsonify({'error': 'Domain is required'}), 400
    if '://' in domain: domain = domain.split('://', 1)[1]
    domain = domain.split('/')[0].split(':')[0]
    port = 443
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.create_connection((domain, port), timeout=10), server_hostname=domain) as s:
            cert = s.getpeercert()
        subject = dict(x[0] for x in cert.get('subject', []))
        issuer = dict(x[0] for x in cert.get('issuer', []))
        not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
        not_after  = datetime.strptime(cert['notAfter'],  '%b %d %H:%M:%S %Y %Z')
        now = datetime.utcnow()
        days_left = (not_after - now).days
        sans = []
        for t, v in cert.get('subjectAltName', []):
            if t == 'DNS': sans.append(v)
        return jsonify({
            'domain': domain,
            'valid': True,
            'subject': subject.get('commonName', domain),
            'issuer': issuer.get('organizationName', 'Unknown'),
            'not_before': not_before.strftime('%Y-%m-%d'),
            'not_after': not_after.strftime('%Y-%m-%d'),
            'days_left': days_left,
            'san': sans[:10],
            'version': cert.get('version', 'N/A'),
        })
    except ssl.SSLCertVerificationError as e:
        return jsonify({'domain': domain, 'valid': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5093)
