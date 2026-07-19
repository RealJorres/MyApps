from flask import Flask, request, jsonify, render_template
from PIL import Image, UnidentifiedImageError
import io, struct

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract():
    f = request.files.get('image')
    if not f:
        return jsonify({'error': 'No image provided'}), 400
    count = max(3, min(10, int(request.form.get('count', 6))))
    try:
        try:
            img = Image.open(f.stream).convert('RGB')
        except UnidentifiedImageError:
            return jsonify({'error': 'Invalid or unsupported image file.'}), 400
        # Resize for speed
        img.thumbnail((200, 200))
        # Quantize to get dominant colors
        quantized = img.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
        palette_raw = quantized.getpalette()[:count * 3]
        colors = []
        for i in range(count):
            r, g, b = palette_raw[i*3], palette_raw[i*3+1], palette_raw[i*3+2]
            hex_color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
            # Calculate relative luminance for contrast
            lum = 0.2126*(r/255)**2.2 + 0.7152*(g/255)**2.2 + 0.0722*(b/255)**2.2
            text_color = '#000000' if lum > 0.179 else '#ffffff'
            colors.append({'hex': hex_color, 'r': r, 'g': g, 'b': b, 'text': text_color})
        return jsonify({'colors': colors})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5055)
