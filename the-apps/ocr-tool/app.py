from flask import Flask, request, jsonify, render_template
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file provided'}), 400
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(f.stream)
        lang = request.form.get('lang', 'eng')
        text = pytesseract.image_to_string(img, lang=lang)
        return jsonify({'text': text, 'char_count': len(text), 'word_count': len(text.split())})
    except ImportError:
        return jsonify({'error': 'pytesseract is not installed. Install it with: pip install pytesseract (also requires Tesseract binary: https://github.com/tesseract-ocr/tesseract)'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5037)
