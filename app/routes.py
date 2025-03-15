import time
from flask import render_template, request, jsonify
from app import app
from app.location_finder import process_company_domain

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    domain = request.form.get('domain')

    if not domain:
        return jsonify({"error": "Domain is required"}), 400  

    try:
        print(f"Processing domain: {domain}...")  
        start_time = time.time()

        # Call your function
        result = process_company_domain(domain)

        execution_time = time.time() - start_time
        print(f"Processing took {execution_time:.2f} seconds")

        if not result:
            return jsonify({"error": "No data found for the domain"}), 404  

        return jsonify(result)

    except Exception as e:
        print(f"Error: {str(e)}")  
        return jsonify({"error": str(e)}), 500  
