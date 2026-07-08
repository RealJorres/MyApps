from flask import Flask, request, send_file, jsonify, render_template
import qrcode
from qrcode import constants as qc
import io, base64

app = Flask(__name__)

EC = {'L': qc.ERROR_CORRECT_L, 'M': qc.ERROR_CORRECT_M, 'Q': qc.ERROR_CORRECT_Q, 'H': qc.ERROR_CORRECT_H}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    d = request.json or {}
    text = d.get('text', '')
    text = text.strip() if isinstance(text, str) else ''
    if not text:
        return jsonify({'error': 'Enter some text or URL'}), 400
    try:
        qr = qrcode.QRCode(version=None, error_correction=EC.get(d.get('ec','M'), qc.ERROR_CORRECT_M),
                           box_size=max(1, min(20, int(d.get('size', 10)))), border=4)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color=d.get('fg','#000000'), back_color=d.get('bg','#ffffff'))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return jsonify({'image': b64})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/download', methods=['POST'])
def download():
    d = request.json or {}
    text = d.get('text', '')
    text = text.strip() if isinstance(text, str) else ''
    if not text:
        return jsonify({'error': 'No text'}), 400
    try:
        qr = qrcode.QRCode(version=None, error_correction=EC.get(d.get('ec','M'), qc.ERROR_CORRECT_M),
                           box_size=max(1, min(20, int(d.get('size', 10)))), border=4)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color=d.get('fg','#000000'), back_color=d.get('bg','#ffffff'))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png', as_attachment=True, download_name='qrcode.png')
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=False, port=5003)
