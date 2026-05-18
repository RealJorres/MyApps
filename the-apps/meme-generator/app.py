from flask import Flask, request, send_file, jsonify, render_template
from PIL import Image, ImageDraw, ImageFont
import io, base64

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    d = request.json or {}
    b64 = d.get('image', '')
    if ',' in b64: b64 = b64.split(',')[1]
    top_text = d.get('top', '').upper()
    bottom_text = d.get('bottom', '').upper()
    font_size = max(20, min(120, int(d.get('font_size', 48))))
    text_color = d.get('text_color', '#ffffff')
    stroke_color = d.get('stroke_color', '#000000')
    try:
        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGBA')
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype('arialbd.ttf', font_size)
        except:
            try:
                font = ImageFont.truetype('Arial_Bold.ttf', font_size)
            except:
                font = ImageFont.load_default()
        w, h = img.size
        r = int(text_color[1:3],16); g = int(text_color[3:5],16); b = int(text_color[5:7],16)
        sr = int(stroke_color[1:3],16); sg = int(stroke_color[3:5],16); sb = int(stroke_color[5:7],16)

        def draw_text(text, y_pct):
            if not text: return
            bbox = draw.textbbox((0,0), text, font=font)
            tw = bbox[2]-bbox[0]; th = bbox[3]-bbox[1]
            x = (w - tw) // 2
            y = int(h * y_pct) - th // 2
            for ox, oy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
                draw.text((x+ox, y+oy), text, font=font, fill=(sr,sg,sb,255))
            draw.text((x, y), text, font=font, fill=(r,g,b,255))

        draw_text(top_text, 0.07)
        draw_text(bottom_text, 0.88)
        out = img.convert('RGB')
        buf = io.BytesIO()
        out.save(buf, format='JPEG', quality=92)
        buf.seek(0)
        return send_file(buf, mimetype='image/jpeg', as_attachment=True, download_name='meme.jpg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5062)
