from flask import Flask, request, jsonify, render_template
import requests as req_lib

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/lookup', methods=['POST'])
def lookup():
    d = request.json or {}
    ip = d.get('ip', '').strip()
    try:
        url = f'http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query'
        resp = req_lib.get(url, timeout=8)
        data = resp.json()
        if data.get('status') == 'fail':
            return jsonify({'error': data.get('message', 'Lookup failed')}), 400
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/myip', methods=['GET'])
def my_ip():
    try:
        resp = req_lib.get('http://ip-api.com/json/?fields=status,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query', timeout=8)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5067)
