from flask import Flask, request, send_file, jsonify, render_template
import fitz, io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Images at or below this pixel area are icons/logos — recompressing them costs
# quality for no real size win, so they are left untouched.
_MIN_IMAGE_AREA = 10000  # ~100x100 px


def _recompress_images(doc, jpg_quality):
    """Re-encode embedded raster images as JPEG at the given quality.

    Only replaces an image when the new JPEG is meaningfully smaller than the
    original stream, and never touches tiny images. Any per-image failure is
    swallowed so one awkward image can't fail the whole document.
    Returns the number of images actually replaced.
    """
    replaced = 0
    seen = set()
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen:
                continue
            seen.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.width * pix.height < _MIN_IMAGE_AREA:
                    pix = None
                    continue
                if pix.alpha:                      # JPEG has no alpha channel
                    pix = fitz.Pixmap(pix, 0)
                if pix.n >= 4:                      # CMYK / DeviceN -> RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                jpg = pix.tobytes(output='jpg', jpg_quality=jpg_quality)
                original = doc.extract_image(xref)['image']
                if len(jpg) < len(original) * 0.95:  # only if it actually helps
                    page.replace_image(xref, stream=jpg)
                    replaced += 1
                pix = None
            except Exception:
                continue  # keep the original image on any failure
    return replaced


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/compress', methods=['POST'])
def compress():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file provided'}), 400

    # Slider value 10..100 = target image quality. Lower = smaller file.
    try:
        quality = int(request.form.get('quality', 80))
    except (ValueError, TypeError):
        quality = 80
    quality = max(10, min(100, quality))

    data = f.read()
    if not data:
        return jsonify({'error': 'The uploaded file is empty.'}), 400
    try:
        src = fitz.open(stream=data, filetype='pdf')
    except Exception:
        return jsonify({'error': 'Invalid or corrupted PDF file.'}), 400
    if src.is_encrypted:
        src.close()
        return jsonify({'error': 'This PDF is password-protected. Remove the password and try again.'}), 400

    try:
        original_size = len(data)
        # At the top of the range keep it lossless (structure-only optimisation);
        # otherwise re-encode images at the chosen JPEG quality for real savings.
        if quality < 90:
            _recompress_images(src, max(20, min(90, quality)))

        buf = io.BytesIO()
        src.save(buf, garbage=4, deflate=True, clean=True, deflate_images=True, deflate_fonts=True)
        src.close()
        compressed_size = len(buf.getvalue())

        # Never hand back a bigger file than we were given.
        if compressed_size >= original_size:
            buf = io.BytesIO(data)
            compressed_size = original_size
        buf.seek(0)

        savings = round((1 - compressed_size / original_size) * 100, 1) if original_size else 0.0
        resp = send_file(buf, mimetype='application/pdf', as_attachment=True, download_name='compressed.pdf')
        resp.headers['X-Original-Size'] = str(original_size)
        resp.headers['X-Compressed-Size'] = str(compressed_size)
        resp.headers['X-Savings'] = str(savings)
        resp.headers['Access-Control-Expose-Headers'] = 'X-Original-Size, X-Compressed-Size, X-Savings'
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5059)
