from flask import Flask, request, send_file, jsonify, render_template
import qrcode
from qrcode import constants as qc
import io, base64

app = Flask(__name__)

EC = {'L': qc.ERROR_CORRECT_L, 'M': qc.ERROR_CORRECT_M, 'Q': qc.ERROR_CORRECT_Q, 'H': qc.ERROR_CORRECT_H}

@app.route('/')
def index():
    return render_template('index.html')

def _build_qr(d):
    """Build the QR PNG. Returns (BytesIO, None) or (None, error_message)."""
    text = d.get('text', '')
    text = text.strip() if isinstance(text, str) else ''
    if not text:
        return None, 'Enter some text or URL'
    if len(text.encode('utf-8')) > 2900:
        return None, 'Text is too long for a QR code (max ~2,900 characters)'
    try:
        size = int(d.get('size', 10))
    except (TypeError, ValueError):
        return None, 'size must be a number'
    try:
        qr = qrcode.QRCode(version=None, error_correction=EC.get(d.get('ec','M'), qc.ERROR_CORRECT_M),
                           box_size=max(1, min(20, size)), border=4)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color=d.get('fg','#000000'), back_color=d.get('bg','#ffffff'))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf, None
    except Exception:
        return None, 'Could not generate the QR code. Check the color values and try again.'

@app.route('/api/generate', methods=['POST'])
def generate():
    buf, err = _build_qr(request.json or {})
    if err:
        return jsonify({'error': err}), 400
    return jsonify({'image': base64.b64encode(buf.getvalue()).decode()})

@app.route('/api/download', methods=['POST'])
def download():
    buf, err = _build_qr(request.json or {})
    if err:
        return jsonify({'error': err}), 400
    return send_file(buf, mimetype='image/png', as_attachment=True, download_name='qrcode.png')

if __name__ == '__main__':
    app.run(debug=False, port=5003)
