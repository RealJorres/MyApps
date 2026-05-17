from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

# easyocr reader is loaded once and reused (model download on first use)
_reader = None

def get_reader(langs):
    global _reader
    import easyocr
    lang_list = langs if langs else ['en']
    _reader = easyocr.Reader(lang_list, gpu=False)
    return _reader

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file provided'}), 400
    try:
        import easyocr
        import numpy as np
        from PIL import Image
        lang_param = request.form.get('lang', 'en')
        lang_map = {
            'eng': 'en', 'en': 'en',
            'spa': 'es', 'fra': 'fr', 'deu': 'de',
            'por': 'pt', 'ita': 'it', 'chi_sim': 'ch_sim',
            'jpn': 'ja', 'ara': 'ar',
        }
        lang = lang_map.get(lang_param, lang_param)
        reader = get_reader([lang])
        img = Image.open(f.stream).convert('RGB')
        img_np = np.array(img)
        results = reader.readtext(img_np, detail=0, paragraph=True)
        text = '\n'.join(results)
        return jsonify({
            'text': text,
            'char_count': len(text),
            'word_count': len(text.split()) if text.strip() else 0,
        })
    except ImportError:
        return jsonify({'error': 'easyocr is not installed. Run: pip install easyocr'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5037)
