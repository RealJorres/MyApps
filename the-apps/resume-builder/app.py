from flask import Flask, request, send_file, jsonify, render_template
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 HRFlowable, Table, TableStyle)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
import io

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    d = request.json or {}
    layout = d.get('layout', 'classic')
    primary = colors.HexColor(d.get('color', '#0f766e'))
    buf = io.BytesIO()

    if layout == 'modern':
        _build_modern(d, buf, primary)
    elif layout == 'sidebar':
        _build_sidebar(d, buf, primary)
    else:
        _build_classic(d, buf, primary)

    buf.seek(0)
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name='resume.pdf')


# ── helpers ──────────────────────────────────────────────────────────────────

def _contact_str(d):
    return ' · '.join(p for p in [
        d.get('email'), d.get('phone'), d.get('location'), d.get('linkedin')
    ] if p)

def _st(name, **kw):
    """Shortcut to create a ParagraphStyle."""
    defaults = dict(fontName='Helvetica', textColor=colors.HexColor('#1e293b'), leading=14)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


# ── CLASSIC ──────────────────────────────────────────────────────────────────

def _build_classic(d, buf, primary):
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=18*mm, bottomMargin=18*mm)
    W = colors.white
    gray = colors.HexColor('#64748b')
    muted = colors.HexColor('#94a3b8')
    light = colors.HexColor('#e2e8f0')

    s_name    = _st('cn', fontSize=22, fontName='Helvetica-Bold', textColor=primary,
                    leading=30, spaceAfter=4)
    s_title   = _st('ct', fontSize=11, textColor=gray, leading=15, spaceAfter=3)
    s_contact = _st('cc', fontSize=9,  textColor=colors.HexColor('#475569'),
                    leading=12, spaceAfter=6)
    s_section = _st('cs', fontSize=11, fontName='Helvetica-Bold', textColor=primary,
                    leading=14, spaceBefore=8, spaceAfter=3)
    s_body    = _st('cb', fontSize=9.5, leading=14, spaceAfter=2)
    s_bullet  = _st('cbu', fontSize=9.5, leading=13, spaceAfter=1, leftIndent=10)
    s_item    = _st('ci', fontSize=9.5, fontName='Helvetica-Bold', leading=13, spaceAfter=1)
    s_date    = _st('cd', fontSize=8.5, fontName='Helvetica-Oblique',
                    textColor=muted, leading=12, spaceAfter=2)

    story = []
    story.append(Paragraph(d.get('name') or 'Your Name', s_name))
    if d.get('title'):   story.append(Paragraph(d['title'], s_title))
    c = _contact_str(d)
    if c: story.append(Paragraph(c, s_contact))
    story.append(HRFlowable(width='100%', thickness=1.5, color=primary, spaceAfter=4))

    def section(heading, items):
        if not items: return
        story.append(Paragraph(heading.upper(), s_section))
        story.append(HRFlowable(width='100%', thickness=0.5, color=light, spaceAfter=4))
        for item in items:
            if item.get('title'):
                line = item['title'] + (f" — {item['org']}" if item.get('org') else '')
                story.append(Paragraph(f'<b>{line}</b>', s_item))
            if item.get('date'): story.append(Paragraph(f"<i>{item['date']}</i>", s_date))
            for ln in (item.get('desc') or '').split('\n'):
                if ln.strip(): story.append(Paragraph(f'• {ln.strip()}', s_bullet))
            story.append(Spacer(1, 3))

    if d.get('summary'):
        story.append(Paragraph('SUMMARY', s_section))
        story.append(HRFlowable(width='100%', thickness=0.5, color=light, spaceAfter=4))
        story.append(Paragraph(d['summary'], s_body))

    section('Experience', d.get('experience', []))
    section('Education',  d.get('education',  []))
    section('Projects',   d.get('projects',   []))

    if d.get('skills'):
        story.append(Paragraph('SKILLS', s_section))
        story.append(HRFlowable(width='100%', thickness=0.5, color=light, spaceAfter=4))
        story.append(Paragraph(d['skills'], s_body))

    doc.build(story)


# ── MODERN ───────────────────────────────────────────────────────────────────

def _build_modern(d, buf, primary):
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=0, bottomMargin=18*mm)
    light = colors.HexColor('#e2e8f0')
    muted = colors.HexColor('#94a3b8')

    s_name    = _st('mn', fontSize=24, fontName='Helvetica-Bold', textColor=colors.white,
                    leading=30, spaceAfter=3)
    s_title   = _st('mt', fontSize=12, textColor=colors.HexColor('#e2e8f0'),
                    leading=16, spaceAfter=3)
    s_contact = _st('mc', fontSize=9, textColor=colors.HexColor('#cbd5e1'),
                    leading=13, spaceAfter=0)
    s_section = _st('ms', fontSize=11, fontName='Helvetica-Bold', textColor=primary,
                    leading=14, spaceBefore=10, spaceAfter=2)
    s_body    = _st('mb', fontSize=9.5, leading=14, spaceAfter=2)
    s_bullet  = _st('mbu', fontSize=9.5, leading=13, spaceAfter=1, leftIndent=10)
    s_item    = _st('mi', fontSize=9.5, fontName='Helvetica-Bold', leading=13, spaceAfter=1)
    s_date    = _st('md', fontSize=8.5, fontName='Helvetica-Oblique',
                    textColor=muted, leading=12, spaceAfter=2)

    # Colored header block
    hdr = []
    hdr.append(Paragraph(d.get('name') or 'Your Name', s_name))
    if d.get('title'): hdr.append(Paragraph(d['title'], s_title))
    c = _contact_str(d)
    if c: hdr.append(Paragraph(c, s_contact))

    available = A4[0] - 36*mm
    hdr_tbl = Table([[hdr]], colWidths=[available + 36*mm])
    hdr_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), primary),
        ('TOPPADDING',    (0,0), (-1,-1), 18),
        ('BOTTOMPADDING', (0,0), (-1,-1), 18),
        ('LEFTPADDING',   (0,0), (-1,-1), 18*mm),
        ('RIGHTPADDING',  (0,0), (-1,-1), 18*mm),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))

    story = [hdr_tbl, Spacer(1, 8)]

    def section(heading, items):
        if not items: return
        story.append(Paragraph(heading.upper(), s_section))
        story.append(HRFlowable(width='100%', thickness=2, color=primary, spaceAfter=5))
        for item in items:
            if item.get('title'):
                line = item['title'] + (f" — {item['org']}" if item.get('org') else '')
                story.append(Paragraph(f'<b>{line}</b>', s_item))
            if item.get('date'): story.append(Paragraph(f"<i>{item['date']}</i>", s_date))
            for ln in (item.get('desc') or '').split('\n'):
                if ln.strip(): story.append(Paragraph(f'• {ln.strip()}', s_bullet))
            story.append(Spacer(1, 3))

    if d.get('summary'):
        story.append(Paragraph('SUMMARY', s_section))
        story.append(HRFlowable(width='100%', thickness=2, color=primary, spaceAfter=5))
        story.append(Paragraph(d['summary'], s_body))

    section('Experience', d.get('experience', []))
    section('Education',  d.get('education',  []))
    section('Projects',   d.get('projects',   []))

    if d.get('skills'):
        story.append(Paragraph('SKILLS', s_section))
        story.append(HRFlowable(width='100%', thickness=2, color=primary, spaceAfter=5))
        story.append(Paragraph(d['skills'], s_body))

    doc.build(story)


# ── SIDEBAR ──────────────────────────────────────────────────────────────────

def _build_sidebar(d, buf, primary):
    available = A4[0] - 30*mm
    lw = available * 0.36
    rw = available * 0.64

    muted = colors.HexColor('#94a3b8')
    light = colors.HexColor('#e2e8f0')

    # Left (colored) styles
    sl_name  = _st('sln', fontSize=16, fontName='Helvetica-Bold',
                   textColor=colors.white, leading=22, spaceAfter=3)
    sl_title = _st('slt', fontSize=9.5, textColor=colors.HexColor('#e2e8f0'),
                   leading=13, spaceAfter=10)
    sl_head  = _st('slh', fontSize=8, fontName='Helvetica-Bold',
                   textColor=colors.white, leading=12, spaceBefore=8, spaceAfter=3)
    sl_body  = _st('slb', fontSize=8.5, textColor=colors.HexColor('#e2e8f0'),
                   leading=12, spaceAfter=2)

    # Right styles
    sr_section = _st('srs', fontSize=11, fontName='Helvetica-Bold', textColor=primary,
                     leading=14, spaceBefore=8, spaceAfter=2)
    sr_body    = _st('srb', fontSize=9.5, leading=14, spaceAfter=2)
    sr_bullet  = _st('srbu', fontSize=9.5, leading=13, spaceAfter=1, leftIndent=10)
    sr_item    = _st('sri', fontSize=9.5, fontName='Helvetica-Bold', leading=13, spaceAfter=1)
    sr_date    = _st('srd', fontSize=8.5, fontName='Helvetica-Oblique',
                     textColor=muted, leading=12, spaceAfter=2)

    # Build left column
    left = []
    left.append(Paragraph(d.get('name') or 'Your Name', sl_name))
    if d.get('title'): left.append(Paragraph(d['title'], sl_title))

    left.append(Paragraph('CONTACT', sl_head))
    for field in ['email', 'phone', 'location', 'linkedin']:
        if d.get(field): left.append(Paragraph(d[field], sl_body))

    if d.get('skills'):
        left.append(Spacer(1, 4))
        left.append(Paragraph('SKILLS', sl_head))
        for sk in d['skills'].split(','):
            if sk.strip(): left.append(Paragraph(f'• {sk.strip()}', sl_body))

    # Build right column
    right = []

    def rsection(heading, items):
        if not items: return
        right.append(Paragraph(heading.upper(), sr_section))
        right.append(HRFlowable(width='100%', thickness=0.5, color=light, spaceAfter=4))
        for item in items:
            if item.get('title'):
                line = item['title'] + (f" — {item['org']}" if item.get('org') else '')
                right.append(Paragraph(f'<b>{line}</b>', sr_item))
            if item.get('date'): right.append(Paragraph(f"<i>{item['date']}</i>", sr_date))
            for ln in (item.get('desc') or '').split('\n'):
                if ln.strip(): right.append(Paragraph(f'• {ln.strip()}', sr_bullet))
            right.append(Spacer(1, 3))

    if d.get('summary'):
        right.append(Paragraph('SUMMARY', sr_section))
        right.append(HRFlowable(width='100%', thickness=0.5, color=light, spaceAfter=4))
        right.append(Paragraph(d['summary'], sr_body))

    rsection('Experience', d.get('experience', []))
    rsection('Education',  d.get('education',  []))
    rsection('Projects',   d.get('projects',   []))

    tbl = Table([[left, right]], colWidths=[lw, rw])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (0,-1), primary),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING',    (0,0), (0,-1), 20),
        ('BOTTOMPADDING', (0,0), (0,-1), 20),
        ('LEFTPADDING',   (0,0), (0,-1), 14),
        ('RIGHTPADDING',  (0,0), (0,-1), 12),
        ('TOPPADDING',    (1,0), (1,-1), 16),
        ('BOTTOMPADDING', (1,0), (1,-1), 16),
        ('LEFTPADDING',   (1,0), (1,-1), 14),
        ('RIGHTPADDING',  (1,0), (1,-1), 6),
    ]))

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=15*mm, leftMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    doc.build([tbl])


if __name__ == '__main__':
    app.run(debug=False, port=5060)
