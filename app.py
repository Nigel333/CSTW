from flask import Flask, request, render_template, send_from_directory, jsonify
import os
import subprocess
from datetime import datetime
from syllables import syllable_map

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def index():
    return render_template('modules.html') 

@app.route('/greetings')
def greetings():
    return render_template('greetings.html')

@app.route('/greetingsBack')
def greetingsBack():
    return render_template('greetings.html')

@app.route('/directions')
def directions():
    return render_template('directions.html')

@app.route('/directionsBack')
def directionsBack():
    return render_template('directions.html')

@app.route('/people')
def people():
    return render_template('people.html')

@app.route('/peopleBack')
def peopleBack():
    return render_template('people.html')

@app.route('/numbers')
def numbers():
    return render_template('numbers.html')

@app.route('/numbersBack')
def numbersBack():
    return render_template('numbers.html')

@app.route('/basic')
def basic():
    return render_template('basic.html')

@app.route('/basicBack')
def basicBack():
    return render_template('basic.html')

#Greetings routes
@app.route('/Maayong_Buntag')
def maayong_buntag():
    audio_file = "Maayong_Buntag.wav"
    return render_template('greetings/Maayong_Buntag.html', audio_file=audio_file)

@app.route('/Maayong_Udto')
def maayong_udto():
    audio_file = "Maayong_Udto.wav"
    return render_template('greetings/Maayong_Udto.html', audio_file=audio_file)

@app.route('/Maayong_Hapon')
def maayong_hapon():
    audio_file = "Maayong_Hapon.wav"
    return render_template('greetings/Maayong_Hapon.html', audio_file=audio_file)

@app.route('/Maayong_Gabii')
def maayong_gabii():
    audio_file = "Maayong_Gabii.wav"
    return render_template('greetings/Maayong_Gabii.html', audio_file=audio_file)

@app.route('/Maayong_Adlaw')
def maayong_adlaw():
    audio_file = "Maayong_Adlaw.wav"
    return render_template('greetings/Maayong_Adlaw.html', audio_file=audio_file)

@app.route('/Kumusta_Ka')
def kumusta_ka():
    audio_file = "Kumusta_Ka.wav"
    return render_template('greetings/Kumusta_Ka.html', audio_file=audio_file)

#Directions routes
@app.route('/Didto')
def didto():
    audio_file = "Didto.wav"
    return render_template('directions/Didto.html', audio_file=audio_file)

@app.route('/Dani')
def dani():
    audio_file = "Dani.wav"
    return render_template('directions/Dani.html', audio_file=audio_file)

@app.route('/Wala')
def wala():
    audio_file = "Wala.wav"
    return render_template('directions/Wala.html', audio_file=audio_file)

@app.route('/Too')
def too():
    audio_file = "Too.wav"
    return render_template('directions/Too.html', audio_file=audio_file)

@app.route('/Asa_Ang')
def asa_ang():
    audio_file = "asa_ang.wav"
    return render_template('directions/Asa_Ang.html', audio_file=audio_file)

@app.route('/Taas')
def taas():
    audio_file = "Taas.wav"
    return render_template('directions/Taas.html', audio_file=audio_file)

@app.route('/Ubos')
def ubos():
    audio_file = "Ubos.wav"
    return render_template('directions/Ubos.html', audio_file=audio_file)

@app.route('/Atubangan')
def atubangan():
    audio_file = "Atubangan.wav"
    return render_template('directions/Atubangan.html', audio_file=audio_file)

@app.route('/Likod')
def likod():
    audio_file = "Likod.wav"
    return render_template('directions/Likod.html', audio_file=audio_file)

#People routes
@app.route('/Ikaw')
def ikaw():
    audio_file = "Ikaw.wav"
    return render_template('people/Ikaw.html', audio_file=audio_file)

@app.route('/Ako')
def ako():
    audio_file = "Ako.wav"
    return render_template('people/Ako.html', audio_file=audio_file)

@app.route('/Siya')
def siya():
    audio_file = "Siya.wav"
    return render_template('people/Siya.html', audio_file=audio_file)

@app.route('/Sila')
def sila():
    audio_file = "Sila.wav"
    return render_template('people/Sila.html', audio_file=audio_file)

@app.route('/Imoha')
def imoha():
    audio_file = "Imoha.wav"
    return render_template('people/Imoha.html', audio_file=audio_file)

@app.route('/Imohang')
def imohang():
    audio_file = "Imohang.wav"
    return render_template('people/Imohang.html', audio_file=audio_file)

@app.route('/Akoa')
def akoa():
    audio_file = "Akoa.wav"
    return render_template('people/Akoa.html', audio_file=audio_file)

@app.route('/Akoang')
def akoang():
    audio_file = "Akoang.wav"
    return render_template('people/Akoang.html', audio_file=audio_file)

@app.route('/Anak')
def anak():
    audio_file = "Anak.wav"
    return render_template('people/Anak.html', audio_file=audio_file)

@app.route('/Bata')
def bata():
    audio_file = "Bata.wav"
    return render_template('people/Bata.html', audio_file=audio_file)

@app.route('/Inahan')
def inahan():
    audio_file = "Inahan.wav"
    return render_template('people/Inahan.html', audio_file=audio_file)

@app.route('/Amahan')
def amahan():
    audio_file = "Amahan.wav"
    return render_template('people/Amahan.html', audio_file=audio_file)

@app.route('/Bana')
def bana():
    audio_file = "Bana.wav"
    return render_template('people/Bana.html', audio_file=audio_file)

@app.route('/Asawa')
def asawa():
    audio_file = "Asawa.wav"
    return render_template('people/Asawa.html', audio_file=audio_file)

#Numbers routes
@app.route('/Wala_None')
def wala_none():
    audio_file = "Wala_None.wav"
    return render_template('numbers/Wala_None.html', audio_file=audio_file)

@app.route('/Isa')
def isa():
    audio_file = "Isa.wav"
    return render_template('numbers/Isa.html', audio_file=audio_file)

@app.route('/Duha')
def duha():
    audio_file = "Duha.wav"
    return render_template('numbers/Duha.html', audio_file=audio_file)

@app.route('/Tulo')
def tulo():
    audio_file = "Tulo.wav"
    return render_template('numbers/Tulo.html', audio_file=audio_file)

@app.route('/Upat')
def upat():
    audio_file = "Upat.wav"
    return render_template('numbers/Upat.html', audio_file=audio_file)

@app.route('/Lima')
def lima():
    audio_file = "Lima.wav"
    return render_template('numbers/Lima.html', audio_file=audio_file)

@app.route('/Unom')
def unom():
    audio_file = "Unom.wav"
    return render_template('numbers/Unom.html', audio_file=audio_file)

@app.route('/Pito')
def pito():
    audio_file = "Pito.wav"
    return render_template('numbers/Pito.html', audio_file=audio_file)

@app.route('/Walo')
def walo():
    audio_file = "Walo.wav"
    return render_template('numbers/Walo.html', audio_file=audio_file)

@app.route('/Siyam')
def siyam():
    audio_file = "Siyam.wav"
    return render_template('numbers/Siyam.html', audio_file=audio_file)

@app.route('/Napulo')
def napulo():
    audio_file = "Napulo.wav"
    return render_template('numbers/Napulo.html', audio_file=audio_file)

@app.route('/Tanan')
def tanan():
    audio_file = "Tanan.wav"
    return render_template('numbers/Tanan.html', audio_file=audio_file)

#Basic routes
@app.route('/Kabalo_Ka_Mag_Tagalog')
def kabalo_ka_mag_tagalog():
    audio_file = "Kabalo_Ka_Mag_Tagalog.wav"
    return render_template('basic/Kabalo_Ka_Mag_Tagalog.html', audio_file=audio_file)

@app.route('/Kabalo_Ka_Mag_English')
def kabalo_ka_mag_english():
    audio_file = "Kabalo_Ka_Mag_English.wav"
    return render_template('basic/Kabalo_Ka_Mag_English.html', audio_file=audio_file)

@app.route('/Palihog')
def palihog():
    audio_file = "Palihog.wav"
    return render_template('basic/Palihog.html', audio_file=audio_file)

@app.route('/Mangayo_Ko_Ug_Menu')
def mangayo_ko_ug_menu():
    audio_file = "Mangayo_Ko_Ug_Menu.wav"
    return render_template('basic/Mangayo_Ko_Ug_Menu.html', audio_file=audio_file)

@app.route('/Palihog_Ko_Ug_Menu')
def palihog_ko_ug_menu():
    audio_file = "Palihog_Ko_Ug_Menu.wav"
    return render_template('basic/Palihog_Ko_Ug_Menu.html', audio_file=audio_file)

@app.route('/Akoang_Anak')
def akoang_anak():
    audio_file = "Akoang_Anak.wav"
    return render_template('basic/Akoang_Anak.html', audio_file=audio_file)

@app.route('/Akoang_Amahan')
def akoang_amahan():
    audio_file = "Akoang_Amahan.wav"
    return render_template('basic/Akoang_Amahan.html', audio_file=audio_file)

@app.route('/Akoa_Nang_Anak')
def akoa_nang_anak():
    audio_file = "Akoa_Nang_Anak.wav"
    return render_template('basic/Akoa_Nang_Anak.html', audio_file=audio_file)

@app.route('/Akoa_Nang_Inahan')
def akoa_nang_inahan():
    audio_file = "Akoa_Nang_Inahan.wav"
    return render_template('basic/Akoa_Nang_Inahan.html', audio_file=audio_file)

@app.route('/Iyaha_Ning_Bana')
def iyaha_ning_bana():
    audio_file = "Iyaha_Ning_Bana.wav"
    return render_template('basic/Iyaha_Ning_Bana.html', audio_file=audio_file)

@app.route('/Siya_Ang_Akoang_Asawa')
def siya_ang_akoang_asawa():
    audio_file = "Siya_Ang_Akoang_Asawa.wav"
    return render_template('basic/Siya_Ang_Akoang_Asawa.html', audio_file=audio_file)

@app.route('/Sila_Akoang_Mga_Anak')
def sila_akoang_mga_anak():
    audio_file = "Sila_Akoang_Mga_Anak.wav"
    return render_template('basic/Sila_Akoang_Mga_Anak.html', audio_file=audio_file)



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
    
    try:
        subprocess.run(["./run.sh"], check=True, shell=True)
        print("Shell script executed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        return f"Error running script: {e}", 500

    result_file = os.path.join('results/', f"{page_name}_result.txt")
    try:
        with open(result_file, 'r') as f:
            color_code = f.read().strip()
    except FileNotFoundError:
        return 'Result file not found', 500
    
    syllables = syllable_map.get(page_name, [])
    print(f"pagename: {syllables}")
    return jsonify({
        "message": "Audio uploaded and script executed successfully",
        "color_code": color_code,
        "syllables": syllables
    })
    
@app.route('/processed_audio/<filename>')
def processed_audio(filename):
    return send_from_directory('processed_audio', filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
