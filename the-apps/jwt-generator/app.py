from flask import Flask, request, jsonify, render_template
import jwt as pyjwt, json, time

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    d = request.json or {}
    secret = d.get('secret', 'your-secret')
    algorithm = d.get('algorithm', 'HS256')
    payload = d.get('payload', {})
    try:
        if isinstance(payload, str):
            payload = json.loads(payload)
        token = pyjwt.encode(payload, secret, algorithm=algorithm)
        return jsonify({'token': token})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/decode', methods=['POST'])
def decode():
    d = request.json or {}
    token = d.get('token', '').strip()
    secret = d.get('secret', '')
    try:
        if secret:
            payload = pyjwt.decode(token, secret, algorithms=['HS256','HS384','HS512','RS256'])
        else:
            payload = pyjwt.decode(token, options={"verify_signature": False}, algorithms=['HS256','HS384','HS512','RS256'])
        return jsonify({'payload': payload, 'verified': bool(secret)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=False, port=5088)
