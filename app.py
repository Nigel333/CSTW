from flask import Flask, request, render_template
import os
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def index():
    return render_template('modules.html') 

@app.route('/greetings')
def greetings():
    return render_template('greetings.html')

@app.route('/directions')
def directions():
    return render_template('directions.html')

@app.route('/people')
def people():
    return render_template('people.html')

@app.route('/numbers')
def numbers():
    return render_template('numbers.html')

@app.route('/basic')
def basic():
    return render_template('basic.html')

@app.route('/Maayong_Buntag')
def maayong_buntag():
    return render_template('greetings/Maayong_Buntag.html')

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return 'No audio file part', 400

    file = request.files['audio']
    if file.filename == '':
        return 'No selected file', 400

    page_name = request.form.get('page_name')
    if not page_name:
        return 'No page name provided', 400

    filename = f"{page_name}99m.wav" # add gender here
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    print(f"Saved: {filepath}")
    return 'Audio uploaded successfully', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
