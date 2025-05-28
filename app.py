from flask import Flask, request, redirect, render_template,make_response, session, send_from_directory, jsonify
from functools import wraps
import os
import logging
from logging.handlers import RotatingFileHandler
import time
import threading
import mysql.connector
from functions import * #functions.py
from datetime import datetime, timedelta
from syllables import syllable_map

DEBUG_FLAG = False #localhost debuggging only
TIMEOUT_DURATION = timedelta(seconds=300) # Session timeout time
MAX_LOGIN_ATTEMPTS = 5  # Maximum failed login attempts before timeout
LOCKOUT_DURATION = 20  # Lockout duration in seconds

app = Flask(__name__)

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="secdevS15",
    database="cwts"
)

# Make directories
UPLOAD_FOLDER = 'uploads'
LOG_FOLDER = 'logs'
USERDATA_FOLDER = 'user_data'
for folder in [UPLOAD_FOLDER, LOG_FOLDER, USERDATA_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Logging config
logger = logging.getLogger('cebuano_tutor')
logger.handlers.clear()
logger.setLevel(logging.INFO)
logger.propagate = False

# Rotating file handler (10MB max size, keep 3 backup files)
file_handler = RotatingFileHandler(
    os.path.join(LOG_FOLDER, 'server.log'), 
    maxBytes=10*1024*1024, 
    backupCount=3
)

# Log format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Console handler for debug
if DEBUG_FLAG:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Add handlers to logger
logger.handlers.clear()
logger.addHandler(file_handler)
logger.propagate = False

# Session settings
app.config['SECRET_KEY'] = os.urandom(12)  # Secure random key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15) # Session timeout failsafe
app.config['SESSION_TYPE'] = 'filesystem'

# Track IP addresses instead of usernames
ip_attempt_tracker = {}  # Dictionary of [ip_address, attempt_count] pairs
ip_timeout_list = []     # List of IP addresses that are currently timed out

logger.info(f"New server session started")

def start_background_timer(ip_address, rem):
    def timer_function():
        logger.info(f'Countdown for IP {ip_address} started')
        time.sleep(LOCKOUT_DURATION)  # Wait for the specified duration
        logger.info(f'Countdown for IP {ip_address} finished')
        if not stop_event.is_set():
            timer_end(ip_address, rem)  # Call the callback function
    stop_event = threading.Event()

    timer_thread = threading.Thread(target=timer_function)
    timer_thread.start()

    return stop_event, timer_thread

def timer_end(ip_address, rem):
    global ip_attempt_tracker
    global ip_timeout_list
    if ip_address in ip_attempt_tracker:
        del ip_attempt_tracker[ip_address]
    if rem:
        ip_timeout_list.remove(ip_address)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        name = session.get('username')
        if not name:  # Check if logged in
            return redirect('/login')  # Redirect to login
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def check_session_timeout():
    # Check if logged in
    if 'username' in session:
        # Get last activity time
        last_activity_str = session.get('last_activity')
        if last_activity_str:
            last_activity = datetime.strptime(last_activity_str, '%Y-%m-%d %H:%M:%S')
            if (datetime.now() - last_activity > TIMEOUT_DURATION):
                logger.info(f"Session with username [{session.get('username')}] timed out")
                session.clear()
                return render_template('login.html', error_message = "Session Timeout, Please Log in again")
            else:
                # Update activity time
                session['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            # If there's no last activity time, set one
            session['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def index():
    name = session.get('username')
    if name:  # If logged in, redirect to modules
        return redirect('/modules')
    return render_template('home.html') 

@app.route('/modules')
@login_required
def modules():
    name = session.get('username')    
    return render_template('modules.html', username=name) 

@app.route('/login')
def loginPage():
    return render_template('login.html')

@app.route('/submit_login', methods=['POST'])
def login():
    global ip_attempt_tracker
    global ip_timeout_list
    
    ip_address = request.remote_addr # Client IP address
    
    if ip_address in ip_timeout_list: # Check if IP is already in timeout
        error_message = "Too many failed login attempts. Please try again later."
        logger.warning(f"IP address [{ip_address}] locked out for too many login attempts")
        return render_template('login.html', error_message=error_message)
    
    [username,flag] = checkLogin(request.form['username'],request.form['password'])
    if flag != -1: # LOGIN
        session.permanent = True  # Permanent session (session exist after browser closing)
        session['username'] = username
        session['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"IP address [{ip_address}] logged in with username [{username}]")
        
        # Clear attempts for IP
        if ip_address in ip_attempt_tracker:
            del ip_attempt_tracker[ip_address]
        return redirect('/modules')

    else:  # Failed login
        # Check if IP is already being tracked
        logger.info(f"IP address [{ip_address}] attempting to login with username [{username}].")
        if ip_address not in ip_attempt_tracker:
            ip_attempt_tracker[ip_address] = 1
        else:
            ip_attempt_tracker[ip_address] += 1  # Inc attempt
            # If max attempts reached
            if ip_attempt_tracker[ip_address] >= MAX_LOGIN_ATTEMPTS:
                logger.warning(f"IP {ip_address} has been timed out due to excessive failed login attempts")
                ip_timeout_list.append(ip_address)
                stop_event, thread = start_background_timer(ip_address, 1)         
    
    return render_template('login.html', username=username, error_message = "Invalid username or password!")

@app.route('/logout')
def logout():
    name = session.get('username')
    logger.info(f"User [{name}] logged out")
    session.clear()
    return redirect('/') #make_response(render_template('/home.html'))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/submitRegister', methods=['POST'])
def submit():
    idnum = getID(1)
    username = request.form['username']
    email = request.form['email']
    firstName = request.form['firstName']
    lastName = request.form['lastName']
    password = request.form['password']
    confirmPass = request.form['confirmPassword']

    # New user validation
    flag = newUserCheck(username,email,firstName,lastName,password,confirmPass)
    
    if flag == 1:
        insertNewUser(idnum, username, firstName, lastName, email, password)
        user_folder = f"{USERDATA_FOLDER}/audio/{username}"
        os.makedirs(user_folder)
        logger.info(f"User [{username}] was registered")
        return render_template('login.html', username=username)
    if flag == 0:
        error_message = "Passwords don't match!"
    if flag == -1:
        error_message = "Username or Email in use!"
    
    return render_template('/register.html',email=email, firstName=firstName, lastName=lastName,
                           username=username, error_message = error_message)

@app.route('/greetings')
@login_required
def greetings():
    return render_template('greetings.html')

@app.route('/greetingsBack')
@login_required
def greetingsBack():
    return render_template('greetings.html')

@app.route('/directions')
@login_required
def directions():
    return render_template('directions.html')

@app.route('/directionsBack')
@login_required
def directionsBack():
    return render_template('directions.html')

@app.route('/people')
@login_required
def people():
    return render_template('people.html')

@app.route('/peopleBack')
@login_required
def peopleBack():
    return render_template('people.html')

@app.route('/numbers')
@login_required
def numbers():
    return render_template('numbers.html')

@app.route('/numbersBack')
@login_required
def numbersBack():
    return render_template('numbers.html')

@app.route('/basic')
@login_required
def basic():
    return render_template('basic.html')

@app.route('/basicBack')
@login_required
def basicBack():
    return render_template('basic.html')

#Greetings routes
@app.route('/Maayong_Buntag')
@login_required
def maayong_buntag():
    audio_file = "Maayong_Buntag.wav"
    return render_template('greetings/Maayong_Buntag.html', audio_file=audio_file)

@app.route('/Maayong_Udto')
@login_required
def maayong_udto():
    audio_file = "Maayong_Udto.wav"
    return render_template('greetings/Maayong_Udto.html', audio_file=audio_file)

@app.route('/Maayong_Hapon')
@login_required
def maayong_hapon():
    audio_file = "Maayong_Hapon.wav"
    return render_template('greetings/Maayong_Hapon.html', audio_file=audio_file)

@app.route('/Maayong_Gabii')
@login_required
def maayong_gabii():
    audio_file = "Maayong_Gabii.wav"
    return render_template('greetings/Maayong_Gabii.html', audio_file=audio_file)

@app.route('/Maayong_Adlaw')
@login_required
def maayong_adlaw():
    audio_file = "Maayong_Adlaw.wav"
    return render_template('greetings/Maayong_Adlaw.html', audio_file=audio_file)

@app.route('/Kumusta_Ka')
@login_required
def kumusta_ka():
    audio_file = "Kumusta_Ka.wav"
    return render_template('greetings/Kumusta_Ka.html', audio_file=audio_file)

#Directions routes
@app.route('/Didto')
@login_required
def didto():
    audio_file = "Didto.wav"
    return render_template('directions/Didto.html', audio_file=audio_file)

@app.route('/Dani')
@login_required
def dani():
    audio_file = "Dani.wav"
    return render_template('directions/Dani.html', audio_file=audio_file)

@app.route('/Wala')
@login_required
def wala():
    audio_file = "Wala.wav"
    return render_template('directions/Wala.html', audio_file=audio_file)

@app.route('/Too')
@login_required
def too():
    audio_file = "Too.wav"
    return render_template('directions/Too.html', audio_file=audio_file)

@app.route('/Asa_Ang')
@login_required
def asa_ang():
    audio_file = "asa_ang.wav"
    return render_template('directions/Asa_Ang.html', audio_file=audio_file)

@app.route('/Taas')
@login_required
def taas():
    audio_file = "Taas.wav"
    return render_template('directions/Taas.html', audio_file=audio_file)

@app.route('/Ubos')
@login_required
def ubos():
    audio_file = "Ubos.wav"
    return render_template('directions/Ubos.html', audio_file=audio_file)

@app.route('/Atubangan')
@login_required
def atubangan():
    audio_file = "Atubangan.wav"
    return render_template('directions/Atubangan.html', audio_file=audio_file)

@app.route('/Likod')
@login_required
def likod():
    audio_file = "Likod.wav"
    return render_template('directions/Likod.html', audio_file=audio_file)

#People routes
@app.route('/Ikaw')
@login_required
def ikaw():
    audio_file = "Ikaw.wav"
    return render_template('people/Ikaw.html', audio_file=audio_file)

@app.route('/Ako')
@login_required
def ako():
    audio_file = "Ako.wav"
    return render_template('people/Ako.html', audio_file=audio_file)

@app.route('/Siya')
@login_required
def siya():
    audio_file = "Siya.wav"
    return render_template('people/Siya.html', audio_file=audio_file)

@app.route('/Sila')
@login_required
def sila():
    audio_file = "Sila.wav"
    return render_template('people/Sila.html', audio_file=audio_file)

@app.route('/Imoha')
@login_required
def imoha():
    audio_file = "Imoha.wav"
    return render_template('people/Imoha.html', audio_file=audio_file)

@app.route('/Imohang')
@login_required
def imohang():
    audio_file = "Imohang.wav"
    return render_template('people/Imohang.html', audio_file=audio_file)

@app.route('/Akoa')
@login_required
def akoa():
    audio_file = "Akoa.wav"
    return render_template('people/Akoa.html', audio_file=audio_file)

@app.route('/Akoang')
@login_required
def akoang():
    audio_file = "Akoang.wav"
    return render_template('people/Akoang.html', audio_file=audio_file)

@app.route('/Anak')
@login_required
def anak():
    audio_file = "Anak.wav"
    return render_template('people/Anak.html', audio_file=audio_file)

@app.route('/Bata')
@login_required
def bata():
    audio_file = "Bata.wav"
    return render_template('people/Bata.html', audio_file=audio_file)

@app.route('/Inahan')
@login_required
def inahan():
    audio_file = "Inahan.wav"
    return render_template('people/Inahan.html', audio_file=audio_file)

@app.route('/Amahan')
@login_required
def amahan():
    audio_file = "Amahan.wav"
    return render_template('people/Amahan.html', audio_file=audio_file)

@app.route('/Bana')
@login_required
def bana():
    audio_file = "Bana.wav"
    return render_template('people/Bana.html', audio_file=audio_file)

@app.route('/Asawa')
@login_required
def asawa():
    audio_file = "Asawa.wav"
    return render_template('people/Asawa.html', audio_file=audio_file)

#Numbers routes
@app.route('/Wala_None')
@login_required
def wala_none():
    audio_file = "Wala_None.wav"
    return render_template('numbers/Wala_None.html', audio_file=audio_file)

@app.route('/Isa')
@login_required
def isa():
    audio_file = "Isa.wav"
    return render_template('numbers/Isa.html', audio_file=audio_file)

@app.route('/Duha')
@login_required
def duha():
    audio_file = "Duha.wav"
    return render_template('numbers/Duha.html', audio_file=audio_file)

@app.route('/Tulo')
@login_required
def tulo():
    audio_file = "Tulo.wav"
    return render_template('numbers/Tulo.html', audio_file=audio_file)

@app.route('/Upat')
@login_required
def upat():
    audio_file = "Upat.wav"
    return render_template('numbers/Upat.html', audio_file=audio_file)

@app.route('/Lima')
@login_required
def lima():
    audio_file = "Lima.wav"
    return render_template('numbers/Lima.html', audio_file=audio_file)

@app.route('/Unom')
@login_required
def unom():
    audio_file = "Unom.wav"
    return render_template('numbers/Unom.html', audio_file=audio_file)

@app.route('/Pito')
@login_required
def pito():
    audio_file = "Pito.wav"
    return render_template('numbers/Pito.html', audio_file=audio_file)

@app.route('/Walo')
@login_required
def walo():
    audio_file = "Walo.wav"
    return render_template('numbers/Walo.html', audio_file=audio_file)

@app.route('/Siyam')
@login_required
def siyam():
    audio_file = "Siyam.wav"
    return render_template('numbers/Siyam.html', audio_file=audio_file)

@app.route('/Napulo')
@login_required
def napulo():
    audio_file = "Napulo.wav"
    return render_template('numbers/Napulo.html', audio_file=audio_file)

@app.route('/Tanan')
@login_required
def tanan():
    audio_file = "Tanan.wav"
    return render_template('numbers/Tanan.html', audio_file=audio_file)

#Basic routes
@app.route('/Kabalo_Ka_Mag_Tagalog')
@login_required
def kabalo_ka_mag_tagalog():
    audio_file = "Kabalo_Ka_Mag_Tagalog.wav"
    return render_template('basic/Kabalo_Ka_Mag_Tagalog.html', audio_file=audio_file)

@app.route('/Kabalo_Ka_Mag_English')
@login_required
def kabalo_ka_mag_english():
    audio_file = "Kabalo_Ka_Mag_English.wav"
    return render_template('basic/Kabalo_Ka_Mag_English.html', audio_file=audio_file)

@app.route('/Palihog')
@login_required
def palihog():
    audio_file = "Palihog.wav"
    return render_template('basic/Palihog.html', audio_file=audio_file)

@app.route('/Mangayo_Ko_Ug_Menu')
@login_required
def mangayo_ko_ug_menu():
    audio_file = "Mangayo_Ko_Ug_Menu.wav"
    return render_template('basic/Mangayo_Ko_Ug_Menu.html', audio_file=audio_file)

@app.route('/Palihog_Ko_Ug_Menu')
@login_required
def palihog_ko_ug_menu():
    audio_file = "Palihog_Ko_Ug_Menu.wav"
    return render_template('basic/Palihog_Ko_Ug_Menu.html', audio_file=audio_file)

@app.route('/Akoang_Anak')
@login_required
def akoang_anak():
    audio_file = "Akoang_Anak.wav"
    return render_template('basic/Akoang_Anak.html', audio_file=audio_file)

@app.route('/Akoang_Amahan')
@login_required
def akoang_amahan():
    audio_file = "Akoang_Amahan.wav"
    return render_template('basic/Akoang_Amahan.html', audio_file=audio_file)

@app.route('/Akoa_Nang_Anak')
@login_required
def akoa_nang_anak():
    audio_file = "Akoa_Nang_Anak.wav"
    return render_template('basic/Akoa_Nang_Anak.html', audio_file=audio_file)

@app.route('/Akoa_Nang_Inahan')
@login_required
def akoa_nang_inahan():
    audio_file = "Akoa_Nang_Inahan.wav"
    return render_template('basic/Akoa_Nang_Inahan.html', audio_file=audio_file)

@app.route('/Iyaha_Ning_Bana')
@login_required
def iyaha_ning_bana():
    audio_file = "Iyaha_Ning_Bana.wav"
    return render_template('basic/Iyaha_Ning_Bana.html', audio_file=audio_file)

@app.route('/Siya_Ang_Akoang_Asawa')
@login_required
def siya_ang_akoang_asawa():
    audio_file = "Siya_Ang_Akoang_Asawa.wav"
    return render_template('basic/Siya_Ang_Akoang_Asawa.html', audio_file=audio_file)

@app.route('/Sila_Akoang_Mga_Anak')
@login_required
def sila_akoang_mga_anak():
    audio_file = "Sila_Akoang_Mga_Anak.wav"
    return render_template('basic/Sila_Akoang_Mga_Anak.html', audio_file=audio_file)



@app.route('/upload', methods=['POST'])
@login_required
def upload_audio():
    if 'audio' not in request.files:
        return 'No audio file part', 400

    file = request.files['audio']
    if file.filename == '':
        return 'No selected file', 400

    page_name = request.form.get('page_name')
    if not page_name:
        return 'No page name provided', 400
    
    name = session.get('username')
    user_folder = f"{USERDATA_FOLDER}/audio/{name}/{page_name}"
    
    os.makedirs(user_folder, exist_ok=True)

    filename = f"{page_name}99m.wav" # add gender here
    filepath = os.path.join(user_folder, filename)
    file.save(filepath)
    logger.info(f"Data by user [{name}] saved: {filepath}")
    
    '''
    # Insert model response maker script code here
    try:
        subprocess.run(["./run.sh"], check=True, shell=True)
        print("Shell script executed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        return f"Error running script: {e}", 500
    '''

    # RESULT FILE SHOULD BE {user}_result.txt or any way to specify responses to correct user, to be corrected
    result_file = os.path.join('results/', f"{page_name}_result.txt") 
    try:
        with open(result_file, 'r') as f:
            color_code = f.read().strip()
    except FileNotFoundError:
        return 'Result file not found', 500
    
    syllables = syllable_map.get(page_name, [])
    #print(f"pagename: {syllables}")
    #print(f"progress: {color_code}")
    
    # Update user JSON
    updateProgress(name, page_name, color_code)
    logger.info(f"User [{name}] progress updated.")
    
    return jsonify({
        "message": "Audio uploaded and script executed successfully",
        "color_code": color_code,
        "syllables": syllables
    })

# ?
@app.route('/processed_audio/<filename>')
def processed_audio(filename):
    return send_from_directory('processed_audio', filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
