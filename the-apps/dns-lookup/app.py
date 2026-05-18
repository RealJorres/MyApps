from flask import Flask, request, jsonify, render_template
import dns.resolver

app = Flask(__name__)

RECORD_TYPES = ['A', 'AAAA', 'MX', 'TXT', 'CNAME', 'NS', 'SOA', 'PTR']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/lookup', methods=['POST'])
def lookup():
    d = request.json or {}
    domain = d.get('domain', '').strip().lower()
    rtype = d.get('type', 'A').upper()
    if not domain:
        return jsonify({'error': 'Domain is required'}), 400
    if rtype not in RECORD_TYPES:
        rtype = 'A'
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        answers = resolver.resolve(domain, rtype)
        records = []
        for rdata in answers:
            records.append({'value': str(rdata), 'ttl': answers.rrset.ttl})
        return jsonify({'domain': domain, 'type': rtype, 'records': records})
    except dns.resolver.NXDOMAIN:
        return jsonify({'error': f'Domain "{domain}" does not exist'}), 404
    except dns.resolver.NoAnswer:
        return jsonify({'records': [], 'domain': domain, 'type': rtype, 'note': 'No records of this type found'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5068)
