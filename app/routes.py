from flask import render_template, request, jsonify
from app import app
from app.location_finder import process_company_domain

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    domain = request.form.get('domain')
    return jsonify(process_company_domain(domain))