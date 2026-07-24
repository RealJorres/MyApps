from flask import Flask, request, send_file, jsonify, render_template
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from xml.sax.saxutils import escape
import io, json, re
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

MAX_ITEMS = 500


def _text(d, key, default=''):
    v = d.get(key, default)
    return v if isinstance(v, str) else (str(v) if v is not None else default)


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _para(text):
    """User text -> ReportLab Paragraph markup, XML-escaped so names like
    'Widgets <LLC>' render literally instead of being parsed as tags."""
    return escape(text).replace('\n', '<br/>')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def generate():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify({'error': 'Invalid JSON body'}), 400

    items = d.get('items', [])
    if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
        return jsonify({'error': 'items must be a list of objects'}), 400
    if len(items) > MAX_ITEMS:
        return jsonify({'error': f'Too many line items (max {MAX_ITEMS})'}), 400

    color = _text(d, 'color', '#0f766e')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        return jsonify({'error': 'color must be a #rrggbb hex value'}), 400

    try:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        primary = colors.HexColor(color)
        story = []

        # Header
        header_style = ParagraphStyle('header', fontSize=24, fontName='Helvetica-Bold', textColor=primary)
        story.append(Paragraph(_para(_text(d, 'business_name') or 'Your Business'), header_style))
        story.append(Spacer(1, 4*mm))

        if _text(d, 'business_address'):
            story.append(Paragraph(_para(_text(d, 'business_address')), styles['Normal']))
        if _text(d, 'business_email'):
            story.append(Paragraph(_para(_text(d, 'business_email')), styles['Normal']))
        story.append(Spacer(1, 8*mm))

        # Invoice meta
        invoice_number = _text(d, 'invoice_number') or '001'
        meta_data = [
            ['INVOICE', f"#{invoice_number}"],
            ['Date', _text(d, 'date') or datetime.today().strftime('%Y-%m-%d')],
            ['Due Date', _text(d, 'due_date')],
        ]
        if _text(d, 'client_name'):
            meta_data.insert(0, ['Bill To', _text(d, 'client_name')])
        if _text(d, 'client_email'):
            meta_data.append(['Client Email', _text(d, 'client_email')])

        meta_table = Table(meta_data, colWidths=[40*mm, 80*mm])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('TEXTCOLOR', (0,0), (0,0), primary),
            ('FONTSIZE', (0,0), (0,0), 14),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10*mm))

        # Line items — invalid qty/price coerce to 0, matching the live preview
        currency = _text(d, 'currency', '$') or '$'
        rows = [['Description', 'Qty', 'Unit Price', 'Total']]
        subtotal = 0
        for item in items:
            qty = _num(item.get('qty', 1), 0)
            price = _num(item.get('price', 0), 0)
            total = qty * price
            subtotal += total
            rows.append([_text(item, 'description'), str(qty), f"{currency}{price:.2f}", f"{currency}{total:.2f}"])

        tax_rate = _num(d.get('tax_rate', 0), 0)
        tax = subtotal * tax_rate / 100
        grand_total = subtotal + tax

        rows.append(['', '', 'Subtotal', f"{currency}{subtotal:.2f}"])
        if tax_rate:
            rows.append(['', '', f"Tax ({tax_rate}%)", f"{currency}{tax:.2f}"])
        rows.append(['', '', 'TOTAL', f"{currency}{grand_total:.2f}"])

        col_widths = [90*mm, 20*mm, 35*mm, 35*mm]
        items_table = Table(rows, colWidths=col_widths)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('ROWBACKGROUNDS', (0,1), (-1,-4), [colors.white, colors.HexColor('#f8fafc')]),
            ('LINEBELOW', (0,0), (-1,0), 1, primary),
            ('LINEABOVE', (0,-3), (-1,-3), 1, colors.HexColor('#e2e8f0')),
            ('FONTNAME', (2,-1), (-1,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (2,-1), (-1,-1), primary),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(items_table)

        if _text(d, 'notes'):
            story.append(Spacer(1, 8*mm))
            story.append(Paragraph('Notes', ParagraphStyle('noteslabel', fontName='Helvetica-Bold', fontSize=10)))
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(_para(_text(d, 'notes')), styles['Normal']))

        doc.build(story)
        buf.seek(0)
        safe_num = re.sub(r'[^\w\-.]', '_', invoice_number)[:60] or '001'
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f"invoice-{safe_num}.pdf")
    except Exception:
        return jsonify({'error': 'Could not generate the PDF. Please check your inputs and try again.'}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5021)
