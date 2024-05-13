"""
Mock AI Module
This module provides functionalities to process PDF files and generate mock student data.
"""
import os
import random
import string
import logging
import requests
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://localhost:5002", "http://localhost:5001"])

# Ensure uploads directory exists
uploads_dir = os.path.join(app.instance_path, 'uploads')
os.makedirs(uploads_dir, exist_ok=True)

logging.basicConfig(level=logging.DEBUG)

def generate_student_data():
    """
    Generate mock student data.
    """
    student_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    answers = {f"Q{k+1}": f"Answer_{chr(65 + k % 5)}" for k in range(20)}  # A-E for answers
    return {"studentID": student_id, "answers": answers}

def send_json_to_app_server(json_data):
    """
    Send JSON data to the app server.
    """
    logging.debug("Sending JSON data to app server...")
    logging.debug("JSON data before sending: %s", json_data)
    try:
        app_server_url = 'http://localhost:5001/json'
        headers = {'Content-Type': 'application/json'}
        response = requests.post(app_server_url, json=json_data, headers=headers, timeout=5)  # Added timeout
        logging.debug("Response status code: %d", response.status_code)
        logging.debug("Response text: %s", response.text)

        if response.ok:
            logging.info("Successfully sent JSON data to app server")
        else:
            logging.error("Failed to send JSON data to app server: HTTP %d", response.status_code)
    
    except requests.Timeout:
        logging.error("Timeout occurred while sending JSON data to app server")
    except requests.RequestException as e:
        logging.error("Error sending JSON data to app server: %s", e)

def process_pdf(pdf_file):
    """
    Process PDF file and generate student data.
    """
    try:
        reader = PdfReader(pdf_file)
        num_pages = len(reader.pages)
        student_data_list = []

        for _ in range(num_pages):
            student_data = generate_student_data()
            student_data_list.append(student_data)

        return student_data_list
    
    except Exception as e:
        logging.error("Error processing PDF: %s", e)
        return []

@app.route('/mock_ai', methods=['POST'])
def process_pdf_request():
    """
    Handle POST request to process PDF file.
    """
    file_id = request.form.get('file_id')
    logging.debug("File ID received from Flask: %s", file_id)
    
    if 'file' not in request.files:
        logging.error("No file part in the request")
        return jsonify({"status": "error", "message": "No file part in the request"})

    file = request.files['file']

    if file.filename == '':
        logging.error("No selected file")
        return jsonify({"status": "error", "message": "No selected file"})

    if file and file.filename.lower().endswith('.pdf'):
        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join(uploads_dir, filename)
            file.save(file_path)

            # Process PDF file
            student_data_list = process_pdf(file_path)

            # Clean up: remove uploaded PDF
            os.remove(file_path)

            # Prepare JSON response
            final_response = {"students": student_data_list, "file_id": file_id}

            # Send JSON data to app server
            send_json_to_app_server(final_response)

            return jsonify({"status": "success", "data": final_response})

        except Exception as e:
            logging.error("Error processing PDF: %s", e)
            return jsonify({"status": "error", "message": f"Error processing PDF: {e}"})

    else:
        logging.error("Only PDF files are allowed")
        return jsonify({"status": "error", "message": "Only PDF files are allowed"})

if __name__ == '__main__':
    app.run(debug=True, port=5002)
