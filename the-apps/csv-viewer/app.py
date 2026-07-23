from flask import Flask, request, jsonify, render_template
import pandas as pd

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/load', methods=['POST'])
def load():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file'}), 400
    name = f.filename.lower()
    try:
        if name.endswith('.csv'):
            head = f.stream.read(4096)
            f.stream.seek(0)
            if b'\x00' in head:
                return jsonify({'error': 'This is not a text CSV file. Please upload a plain-text .csv.'}), 400
            df = pd.read_csv(f.stream, encoding='utf-8', encoding_errors='replace')
        elif name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f.stream)
        else:
            return jsonify({'error': 'Use CSV or Excel (.xlsx/.xls)'}), 400
        if df.shape[1] == 0:
            return jsonify({'error': 'No columns found. The file appears to be empty or not a valid CSV/Excel file.'}), 400
        df = df.fillna('')
        truncated = len(df) > 10000
        if truncated:
            df = df.head(10000)
        return jsonify({'columns': list(df.columns.astype(str)),
                        'rows': df.astype(str).values.tolist(),
                        'total': len(df), 'truncated': truncated})
    except Exception:
        return jsonify({'error': 'Could not parse this file. Make sure it is a valid CSV or Excel file.'}), 400

if __name__ == '__main__':
    app.run(debug=False, port=5004)
