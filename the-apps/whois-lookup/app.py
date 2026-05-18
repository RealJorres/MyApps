from flask import Flask, request, jsonify, render_template
import whois

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/lookup', methods=['POST'])
def lookup():
    d = request.json or {}
    domain = d.get('domain', '').strip().lower()
    if not domain:
        return jsonify({'error': 'Domain is required'}), 400
    if '://' in domain:
        domain = domain.split('://', 1)[1]
    domain = domain.split('/')[0]
    try:
        w = whois.whois(domain)
        def fmt(v):
            if v is None: return 'N/A'
            if isinstance(v, list): return ', '.join(str(i) for i in v[:3])
            return str(v)
        result = {
            'domain': domain,
            'registrar': fmt(w.registrar),
            'creation_date': fmt(w.creation_date),
            'expiration_date': fmt(w.expiration_date),
            'updated_date': fmt(w.updated_date),
            'name_servers': fmt(w.name_servers),
            'status': fmt(w.status),
            'emails': fmt(w.emails),
            'org': fmt(getattr(w, 'org', None)),
            'country': fmt(getattr(w, 'country', None)),
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5092)
