from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file provided'}), 400
    try:
        import numpy as np
        from PIL import Image
        img = Image.open(f.stream).convert('RGB')
        img_np = np.array(img)
        engine = get_engine()
        result, _ = engine(img_np)
        if not result:
            return jsonify({'text': '', 'char_count': 0, 'word_count': 0})
        text = '\n'.join([line[1] for line in result if line and len(line) > 1])
        return jsonify({
            'text': text,
            'char_count': len(text),
            'word_count': len(text.split()) if text.strip() else 0,
        })
    except ImportError:
        return jsonify({'error': 'rapidocr-onnxruntime is not installed. Run: pip install rapidocr-onnxruntime'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5037)
