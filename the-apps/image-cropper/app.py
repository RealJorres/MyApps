from flask import Flask, request, send_file, jsonify, render_template
from PIL import Image
import io, base64

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/crop', methods=['POST'])
def crop():
    d = request.json or {}
    b64 = d.get('image', '')
    if ',' in b64: b64 = b64.split(',')[1]
    try:
        img_data = base64.b64decode(b64)
        img = Image.open(io.BytesIO(img_data))
        x = int(d.get('x', 0)); y = int(d.get('y', 0))
        w = int(d.get('w', img.width)); h = int(d.get('h', img.height))
        cropped = img.crop((x, y, x+w, y+h))
        buf = io.BytesIO()
        fmt = d.get('format', 'PNG').upper()
        if fmt == 'JPEG' and cropped.mode in ('RGBA','LA','P'):
            bg = Image.new('RGB', cropped.size, (255,255,255))
            if cropped.mode == 'P': cropped = cropped.convert('RGBA')
            bg.paste(cropped, mask=cropped.split()[-1])
            cropped = bg
        cropped.save(buf, format=fmt, quality=92 if fmt == 'JPEG' else None)
        buf.seek(0)
        mime = {'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp'}.get(fmt,'image/png')
        ext = {'PNG':'png','JPEG':'jpg','WEBP':'webp'}.get(fmt,'png')
        return send_file(buf, mimetype=mime, as_attachment=True, download_name=f'cropped.{ext}')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5061)
