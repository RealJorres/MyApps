from flask import Flask, request, send_file, jsonify, render_template
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import io

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    d = request.json or {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    primary = colors.HexColor(d.get('color', '#0f766e'))
    story = []

    name_style = ParagraphStyle('name', fontSize=22, fontName='Helvetica-Bold', textColor=primary, spaceAfter=2)
    title_style = ParagraphStyle('title', fontSize=11, fontName='Helvetica', textColor=colors.HexColor('#64748b'), spaceAfter=4)
    contact_style = ParagraphStyle('contact', fontSize=9, fontName='Helvetica', textColor=colors.HexColor('#475569'), spaceAfter=2)
    section_style = ParagraphStyle('section', fontSize=11, fontName='Helvetica-Bold', textColor=primary, spaceBefore=10, spaceAfter=3)
    body_style = ParagraphStyle('body', fontSize=9.5, fontName='Helvetica', textColor=colors.HexColor('#1e293b'), spaceAfter=2, leading=14)
    bullet_style = ParagraphStyle('bullet', fontSize=9.5, fontName='Helvetica', textColor=colors.HexColor('#1e293b'), spaceAfter=1, leftIndent=10, leading=13)

    story.append(Paragraph(d.get('name', 'Your Name'), name_style))
    if d.get('title'): story.append(Paragraph(d['title'], title_style))
    contact_parts = [p for p in [d.get('email'), d.get('phone'), d.get('location'), d.get('linkedin')] if p]
    if contact_parts: story.append(Paragraph(' · '.join(contact_parts), contact_style))
    story.append(HRFlowable(width='100%', thickness=1.5, color=primary, spaceAfter=6))

    def add_section(title, items):
        if not items: return
        story.append(Paragraph(title.upper(), section_style))
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=4))
        for item in items:
            if item.get('title'):
                row_parts = [item['title']]
                if item.get('org'): row_parts[0] += f" — {item['org']}"
                story.append(Paragraph(f"<b>{row_parts[0]}</b>", body_style))
            if item.get('date'):
                story.append(Paragraph(f"<i>{item['date']}</i>", ParagraphStyle('date', fontSize=8.5, textColor=colors.HexColor('#94a3b8'), spaceAfter=1, fontName='Helvetica-Oblique')))
            if item.get('desc'):
                for line in item['desc'].split('\n'):
                    if line.strip():
                        story.append(Paragraph(f"• {line.strip()}", bullet_style))
            story.append(Spacer(1, 3))

    if d.get('summary'):
        story.append(Paragraph('SUMMARY', section_style))
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=4))
        story.append(Paragraph(d['summary'], body_style))

    add_section('Experience', d.get('experience', []))
    add_section('Education', d.get('education', []))
    add_section('Projects', d.get('projects', []))

    if d.get('skills'):
        story.append(Paragraph('SKILLS', section_style))
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=4))
        story.append(Paragraph(d['skills'], body_style))

    doc.build(story)
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name='resume.pdf')

if __name__ == '__main__':
    app.run(debug=False, port=5060)
