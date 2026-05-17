from flask import Flask, request, send_file, jsonify, render_template
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
import io, json
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    d = request.json or {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    primary = colors.HexColor(d.get('color', '#0f766e'))
    story = []

    # Header
    header_style = ParagraphStyle('header', fontSize=24, fontName='Helvetica-Bold', textColor=primary)
    story.append(Paragraph(d.get('business_name', 'Your Business'), header_style))
    story.append(Spacer(1, 4*mm))

    if d.get('business_address'):
        story.append(Paragraph(d['business_address'].replace('\n','<br/>'), styles['Normal']))
    if d.get('business_email'):
        story.append(Paragraph(d['business_email'], styles['Normal']))
    story.append(Spacer(1, 8*mm))

    # Invoice meta
    meta_data = [
        ['INVOICE', f"#{d.get('invoice_number', '001')}"],
        ['Date', d.get('date', datetime.today().strftime('%Y-%m-%d'))],
        ['Due Date', d.get('due_date', '')],
    ]
    if d.get('client_name'):
        meta_data.insert(0, ['Bill To', d['client_name']])
    if d.get('client_email'):
        meta_data.append(['Client Email', d['client_email']])

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

    # Line items
    items = d.get('items', [])
    currency = d.get('currency', '$')
    rows = [['Description', 'Qty', 'Unit Price', 'Total']]
    subtotal = 0
    for item in items:
        qty = float(item.get('qty', 1))
        price = float(item.get('price', 0))
        total = qty * price
        subtotal += total
        rows.append([item.get('description',''), str(qty), f"{currency}{price:.2f}", f"{currency}{total:.2f}"])

    tax_rate = float(d.get('tax_rate', 0))
    tax = subtotal * tax_rate / 100
    grand_total = subtotal + tax

    rows.append(['', '', 'Subtotal', f"{currency}{subtotal:.2f}"])
    if tax_rate:
        rows.append(['', '', f"Tax ({tax_rate}%)", f"{currency}{tax:.2f}"])
    rows.append(['', '', 'TOTAL', f"{currency}{grand_total:.2f}"])

    col_widths = [90*mm, 20*mm, 35*mm, 35*mm]
    items_table = Table(rows, colWidths=col_widths)
    n = len(rows)
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

    if d.get('notes'):
        story.append(Spacer(1, 8*mm))
        story.append(Paragraph('Notes', ParagraphStyle('noteslabel', fontName='Helvetica-Bold', fontSize=10)))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(d['notes'].replace('\n','<br/>'), styles['Normal']))

    doc.build(story)
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f"invoice-{d.get('invoice_number','001')}.pdf")

if __name__ == '__main__':
    app.run(debug=False, port=5021)
