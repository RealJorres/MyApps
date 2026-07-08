from flask import Flask, request, jsonify, render_template
import csv, json, io

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/csv-to-json', methods=['POST'])
def csv_to_json():
    d = request.json or {}
    text = d.get('text', '')
    delimiter = d.get('delimiter', ',')
    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        rows = [dict(r) for r in reader]
        return jsonify({'result': json.dumps(rows, indent=2, ensure_ascii=False), 'count': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/json-to-csv', methods=['POST'])
def json_to_csv():
    d = request.json or {}
    text = d.get('text', '')
    delimiter = d.get('delimiter', ',')
    try:
        data = json.loads(text)
        if not isinstance(data, list): data = [data]
        if not data: return jsonify({'result': '', 'count': 0})
        keys = list(data[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=keys, delimiter=delimiter, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
        return jsonify({'result': buf.getvalue(), 'count': len(data)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=False, port=5074)
