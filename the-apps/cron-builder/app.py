from flask import Flask, request, jsonify, render_template
from croniter import croniter
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/describe', methods=['POST'])
def describe():
    d = request.json or {}
    expr = d.get('expr', '').strip()
    if not expr:
        return jsonify({'error': 'No expression'}), 400
    try:
        parts = expr.split()
        if len(parts) != 5:
            return jsonify({'error': 'Cron expression must have exactly 5 fields'}), 400
        it = croniter(expr, datetime.now())
        next_runs = [it.get_next(datetime).strftime('%Y-%m-%d %H:%M:%S') for _ in range(5)]
        return jsonify({'valid': True, 'next_runs': next_runs})
    except Exception as e:
        return jsonify({'error': str(e), 'valid': False}), 400

if __name__ == '__main__':
    app.run(debug=False, port=5025)
