from flask import Flask, request, jsonify, render_template
from PIL import Image, ExifTags
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/exif', methods=['POST'])
def exif():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file'}), 400
    try:
        img = Image.open(f.stream)
        info = {'format': img.format or 'Unknown', 'mode': img.mode, 'width': img.width, 'height': img.height, 'size_mp': round(img.width * img.height / 1e6, 2)}
        raw = img._getexif() if hasattr(img, '_getexif') else None
        exif_data = {}
        if raw:
            for tag_id, value in raw.items():
                tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                if isinstance(value, bytes):
                    try: value = value.decode('utf-8', errors='replace')
                    except: value = repr(value)
                elif isinstance(value, tuple) and len(value) == 2:
                    value = f"{value[0]}/{value[1]} ({value[0]/value[1]:.4f})" if value[1] != 0 else str(value)
                exif_data[tag] = str(value)
        return jsonify({'info': info, 'exif': exif_data, 'has_exif': bool(exif_data)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5022)
