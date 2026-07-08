from flask import Flask, request, jsonify, send_file, render_template
import markdown, io, re

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

MAX_TEXT = 150_000  # chars — PDF build time grows sharply beyond this

def _text_of(d):
    v = d.get('text', '')
    return v if isinstance(v, str) else ''

@app.route('/api/render', methods=['POST'])
def render_md():
    d = request.json or {}
    text = _text_of(d)
    if len(text) > MAX_TEXT:
        return jsonify({'error': f'Document too large (max {MAX_TEXT//1000}k characters)'}), 413
    try:
        html = markdown.markdown(text,
               extensions=['fenced_code', 'tables', 'nl2br'])
        return jsonify({'html': html})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Preformatted
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    d = request.json or {}
    md_text = _text_of(d)
    if len(md_text) > MAX_TEXT:
        return jsonify({'error': f'Document too large (max {MAX_TEXT//1000}k characters)'}), 413
    title = d.get('title', 'Document')
    if not isinstance(title, str):
        title = 'Document'
    try:
        font_size = max(8, min(14, int(d.get('font_size', 11))))
    except (TypeError, ValueError):
        font_size = 11
    try:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
            rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)

        h1_style = ParagraphStyle('h1', fontSize=font_size+8, fontName='Helvetica-Bold', spaceAfter=6, spaceBefore=10, textColor=colors.HexColor('#0f766e'))
        h2_style = ParagraphStyle('h2', fontSize=font_size+4, fontName='Helvetica-Bold', spaceAfter=4, spaceBefore=8, textColor=colors.HexColor('#1e293b'))
        h3_style = ParagraphStyle('h3', fontSize=font_size+2, fontName='Helvetica-Bold', spaceAfter=3, spaceBefore=6, textColor=colors.HexColor('#1e293b'))
        body   = ParagraphStyle('body',   fontSize=font_size, fontName='Helvetica', spaceAfter=6, leading=font_size*1.5)
        code_s = ParagraphStyle('code',   fontSize=font_size-1, fontName='Courier', spaceAfter=4, backColor=colors.HexColor('#f1f5f9'), leftIndent=10)
        bullet = ParagraphStyle('bullet', fontSize=font_size, fontName='Helvetica', spaceAfter=3, leftIndent=15, leading=font_size*1.4)

        story = []
        lines = md_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('### '):   story.append(Paragraph(line[4:], h3_style))
            elif line.startswith('## '): story.append(Paragraph(line[3:], h2_style))
            elif line.startswith('# '):  story.append(Paragraph(line[2:], h1_style))
            elif line.startswith('---') or line.startswith('***'):
                story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=4))
            elif line.startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    code_lines.append(lines[i]); i += 1
                story.append(Preformatted('\n'.join(code_lines), code_s))
            elif line.startswith('- ') or line.startswith('* '):
                text = line[2:].replace('**', '<b>', 1).replace('**', '</b>', 1)
                story.append(Paragraph(f'• {text}', bullet))
            elif line.strip():
                text = line.replace('**', '<b>', 1).replace('**', '</b>', 1).replace('*', '<i>', 1).replace('*', '</i>', 1)
                story.append(Paragraph(text, body))
            else:
                story.append(Spacer(1, 4))
            i += 1

        doc.build(story)
        buf.seek(0)
        safe = re.sub(r'[^\w\-]', '_', title)[:40]
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f'{safe}.pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5008)
