from flask import Flask, request, redirect, render_template,make_response, session, send_from_directory, jsonify
from functools import wraps
import os
import logging
from logging.handlers import RotatingFileHandler
import time
import threading
import subprocess
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
    password="password", #secdevS15
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
    print(name)
    if name:  # If logged in, redirect to modules
        return redirect('/modules')
    return render_template('home.html') 

@app.route('/modules')
@login_required
def modules():
    name = session.get('username')    
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('modules.html', username=name, completed=completed, not_completed=not_completed) 

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
    username.strip().replace(" ", "_")
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

    username.strip().replace(" ", "_")

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
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('greetings.html', completed=completed, not_completed=not_completed)

@app.route('/greetingsBack')
@login_required
def greetingsBack():
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('greetings.html', completed=completed, not_completed=not_completed)

@app.route('/directions')
@login_required
def directions():
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('directions.html', completed=completed, not_completed=not_completed)

@app.route('/directionsBack')
@login_required
def directionsBack():
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('directions.html', completed=completed, not_completed=not_completed)

@app.route('/people')
@login_required
def people():
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('people.html', completed=completed, not_completed=not_completed)

@app.route('/peopleBack')
@login_required
def peopleBack():
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('people.html', completed=completed, not_completed=not_completed)

@app.route('/numbers')
@login_required
def numbers():
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('numbers.html', completed=completed, not_completed=not_completed)

@app.route('/numbersBack')
@login_required
def numbersBack():
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('numbers.html', completed=completed, not_completed=not_completed)

@app.route('/basic')
@login_required
def basic():
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('basic.html', completed=completed, not_completed=not_completed)

@app.route('/basicBack')
@login_required
def basicBack():
    data = loadJson(session.get('username'))
    progress_data = data.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('basic.html', completed=completed, not_completed=not_completed)

#Greetings routes
@app.route('/Maayong_Buntag')
@login_required
def maayong_buntag():
    data = {
        "audio_file": "Maayong_Buntag.webm",
        "audio_file2": "Maayong_Buntag2.webm",
        "cebuano_text": "Maayong Buntag!",
        "english_text": "Good Morning!",
        "back_url": "/greetingsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Maayong_Udto')
@login_required
def maayong_udto():
    data = {
        "audio_file": "Maayong_Udto.webm",
        "audio_file2": "Maayong_Udto2.webm",
        "cebuano_text": "Maayong Udto!",
        "english_text": "Good Noon!",
        "back_url": "/greetingsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Maayong_Hapon')
@login_required
def maayong_hapon():
    data = {
        "audio_file": "Maayong_Hapon.webm",
        "audio_file2": "Maayong_Hapon2.webm",
        "cebuano_text": "Maayong Hapon!",
        "english_text": "Good Afternoon!",
        "back_url": "/greetingsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Maayong_Gabii')
@login_required
def maayong_gabii():
    data = {
        "audio_file": "Maayong_Gabii.webm",
         "audio_file2": "Maayong_Gabii2.webm",
        "cebuano_text": "Maayong Gabii!",
        "english_text": "Good Night!",
        "back_url": "/greetingsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Maayong_Adlaw')
@login_required
def maayong_adlaw():
    data = {
        "audio_file": "Maayong_Adlaw.webm",
        "audio_file2": "Maayong_Adlaw2.webm",
        "cebuano_text": "Maayong Adlaw!",
        "english_text": "Good Day!",
        "back_url": "/greetingsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Kumusta_Ka')
@login_required
def kumusta_ka():
    audio_file = "Kumusta_Ka.webm"
    data = {
        "audio_file": "Kumusta_Ka.webm",
        "audio_file2": "Kumusta_Ka2.webm",
        "cebuano_text": "Kumusta Ka?",
        "english_text": "How are you?",
        "back_url": "/greetingsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

#Directions routes
@app.route('/Didto')
@login_required
def didto():
    data = {
        "audio_file": "Didto.webm",
        "audio_file2": "Didto2.webm",
        "cebuano_text": "Didto",
        "english_text": "Over there (far)",
        "back_url": "/directionsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Dani')
@login_required
def dani():
    data = {
        "audio_file": "Dani.webm",
        "audio_file2": "Dani2.webm",
        "cebuano_text": "Dani",
        "english_text": "Here",
        "back_url": "/directionsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Wala')
@login_required
def wala():
    data = {
        "audio_file": "Wala.webm",
        "audio_file2": "Wala2.webm",
        "cebuano_text": "Wala",
        "english_text": "Left",
        "back_url": "/directionsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Too')
@login_required
def too():
    data = {
        "audio_file": "Too.webm",
        "audio_file2": "Too2.webm",
        "cebuano_text": "Too",
        "english_text": "Right",
        "back_url": "/directionsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Asa_Ang')
@login_required
def asa_ang():
    data = {
        "audio_file": "Asa_Ang.webm",
        "audio_file2": "Asa_Ang2.webm",
        "cebuano_text": "Asa Ang",
        "english_text": "Where is",
        "back_url": "/directionsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Taas')
@login_required
def taas():
    data = {
        "audio_file": "Taas.webm",
        "audio_file2": "Taas2.webm",
        "cebuano_text": "Taas",
        "english_text": "Up",
        "back_url": "/directionsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Ubos')
@login_required
def ubos():
    data = {
        "audio_file": "Ubos.webm",
        "audio_file2": "Ubos2.webm",
        "cebuano_text": "Ubos",
        "english_text": "Down",
        "back_url": "/directionsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Atubangan')
@login_required
def atubangan():
    data = {
        "audio_file": "Atubangan.webm",
        "audio_file2": "Atubangan2.webm",
        "cebuano_text": "Atubangan",
        "english_text": "In front",
        "back_url": "/directionsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Likod')
@login_required
def likod():
    data = {
        "audio_file": "Likod.webm",
        "audio_file2": "Likod2.webm",
        "cebuano_text": "Likod",
        "english_text": "Behind",
        "back_url": "/directionsBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
#People routes
@app.route('/Ikaw')
@login_required
def ikaw():
    data = {
        "audio_file": "Ikaw.webm",
        "audio_file2": "Ikaw2.webm",
        "cebuano_text": "Ikaw",
        "english_text": "You",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Ako')
@login_required
def ako():
    data = {
        "audio_file": "Ako.webm",
        "audio_file2": "Ako2.webm",
        "cebuano_text": "Ako",
        "english_text": "Me/I",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Siya')
@login_required
def siya():
    data = {
        "audio_file": "Siya.webm",
        "audio_file2": "Siya2.webm",
        "cebuano_text": "Siya",
        "english_text": "He/She",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Sila')
@login_required
def sila():
    data = {
        "audio_file": "Sila.webm",
        "audio_file2": "Sila2.webm",
        "cebuano_text": "Sila",
        "english_text": "They/Them",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Imoha')
@login_required
def imoha():
    data = {
        "audio_file": "Imoha.webm",
        "audio_file2": "Imoha2.webm",
        "cebuano_text": "Imoha",
        "english_text": "Yours",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Imohang')
@login_required
def imohang():
    data = {
        "audio_file": "Imohang.webm",
        "audio_file2": "Imohang2.webm",
        "cebuano_text": "Imohang",
        "english_text": "Your",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Akoa')
@login_required
def akoa():
    data = {
        "audio_file": "Akoa.webm",
        "audio_file2": "Akoa2.webm",
        "cebuano_text": "Akoa",
        "english_text": "Mine",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Akoang')
@login_required
def akoang():
    data = {
        "audio_file": "Akoang.webm",
        "audio_file2": "Akoang2.webm",
        "cebuano_text": "Akoang",
        "english_text": "My",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Anak')
@login_required
def anak():
    data = {
        "audio_file": "Anak.webm",
        "audio_file2": "Anak2.webm",
        "cebuano_text": "Anak",
        "english_text": "Son/Daughter",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Bata')
@login_required
def bata():
    data = {
        "audio_file": "Bata.webm",
        "audio_file2": "Bata2.webm",
        "cebuano_text": "Bata",
        "english_text": "Child",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Inahan')
@login_required
def inahan():
    data = {
        "audio_file": "Inahan.webm",
        "audio_file2": "Inahan2.webm",
        "cebuano_text": "Inahan",
        "english_text": "Mother",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Amahan')
@login_required
def amahan():
    data = {
        "audio_file": "Amahan.webm",
        "audio_file2": "Amahan2.webm",
        "cebuano_text": "Amahan",
        "english_text": "Father",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Bana')
@login_required
def bana():
    data = {
        "audio_file": "Bana.webm",
        "audio_file2": "Bana2.webm",
        "cebuano_text": "Bana",
        "english_text": "Husband",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Asawa')
@login_required
def asawa():
    data = {
        "audio_file": "Asawa.webm",
        "audio_file2": "Asawa2.webm",
        "cebuano_text": "Asawa",
        "english_text": "Wife",
        "back_url": "/peopleBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

#Numbers routes
@app.route('/Wala_None')
@login_required
def wala_none():
    data = {
        "audio_file": "Wala_None.webm",
        "audio_file2": "Wala_None2.webm",
        "cebuano_text": "Wala",
        "english_text": "None",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Isa')
@login_required
def isa():
    data = {
        "audio_file": "Isa.webm",
        "audio_file2": "Isa2.webm",
        "cebuano_text": "Isa",
        "english_text": "One",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Duha')
@login_required
def duha():
    data = {
        "audio_file": "Duha.webm",
        "audio_file2": "Duha2.webm",
        "cebuano_text": "Duha",
        "english_text": "Two",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Tulo')
@login_required
def tulo():
    data = {
        "audio_file": "Tulo.webm",
        "audio_file2": "Tulo2.webm",
        "cebuano_text": "Tulo",
        "english_text": "Three",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Upat')
@login_required
def upat():
    data = {
        "audio_file": "Upat.webm",
        "audio_file2": "Upat2.webm",
        "cebuano_text": "Upat",
        "english_text": "Four",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Lima')
@login_required
def lima():
    data = {
        "audio_file": "Lima.webm",
        "audio_file2": "Lima2.webm",
        "cebuano_text": "Lima",
        "english_text": "Five",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Unom')
@login_required
def unom():
    data = {
        "audio_file": "Unom.webm",
        "audio_file2": "Unom2.webm",
        "cebuano_text": "Unom",
        "english_text": "Six",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Pito')
@login_required
def pito():
    data = {
        "audio_file": "Pito.webm",
        "audio_file2": "Pito2.webm",
        "cebuano_text": "Pito",
        "english_text": "Seven",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Walo')
@login_required
def walo():
    data = {
        "audio_file": "Walo.webm",
        "audio_file2": "Walo2.webm",
        "cebuano_text": "Walo",
        "english_text": "Eight",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Siyam')
@login_required
def siyam():
    data = {
        "audio_file": "Siyam.webm",
        "audio_file2": "Siyam2.webm",
        "cebuano_text": "Siyam",
        "english_text": "Nine",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Napulo')
@login_required
def napulo():
    data = {
        "audio_file": "Napulo.webm",
        "audio_file2": "Napulo2.webm",
        "cebuano_text": "Napulo",
        "english_text": "Ten",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Tanan')
@login_required
def tanan():
    data = {
        "audio_file": "Tanan.webm",
        "audio_file2": "Tanan2.webm",
        "cebuano_text": "Tanan",
        "english_text": "All",
        "back_url": "/numbersBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

#Basic routes
@app.route('/Kabalo_Ka_Mag_Tagalog')
@login_required
def kabalo_ka_mag_tagalog():
    data = {
        "audio_file": "Kabalo_Ka_Mag_Tagalog.webm",
        "audio_file2": "Kabalo_Ka_Mag_Tagalog2.webm",
        "cebuano_text": "Kabalo Ka Mag Tagalog?",
        "english_text": "Can you speak Tagalog?",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Kabalo_Ka_Mag_English')
@login_required
def kabalo_ka_mag_english():
    data = {
        "audio_file": "Kabalo_Ka_Mag_English.webm",
        "audio_file2": "Kabalo_Ka_Mag_English2.webm",
        "cebuano_text": "Kabalo Ka Mag English?",
        "english_text": "Can you speak English?",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Palihog')
@login_required
def palihog():
    data = {
        "audio_file": "Pahilog.webm",
        "audio_file2": "Pahilog2.webm",
        "cebuano_text": "Pahilog",
        "english_text": "Please/Request",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Mangayo_Ko_Ug_Menu')
@login_required
def mangayo_ko_ug_menu():
    data = {
        "audio_file": "Mangayo_Ko_Ug_Menu.webm",
        "audio_file2": "Mangayo_Ko_Ug_Menu2.webm",
        "cebuano_text": "Mangayo Ko Ug Menu",
        "english_text": "I'd like the menu",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)
    
@app.route('/Palihog_Ko_Ug_Menu')
@login_required
def palihog_ko_ug_menu():
    data = {
        "audio_file": "Palihog_Ko_Ug_Menu.webm",
        "audio_file2": "Palihog_Ko_Ug_Menu2.webm",
        "cebuano_text": "Pahilog Ko Ug Menu",
        "english_text": "Please hand me the menu",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Akoang_Anak')
@login_required
def akoang_anak():
    data = {
        "audio_file": "Akoang_Anak.webm",
        "audio_file2": "Akoang_Anak2.webm",
        "cebuano_text": "Akoang Anak",
        "english_text": "My child",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Akoang_Amahan')
@login_required
def akoang_amahan():
    data = {
        "audio_file": "Akoang_Amahan.webm",
        "audio_file2": "Akoang_Amahan2.webm",
        "cebuano_text": "Akoang Amahan",
        "english_text": "My father",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Akoa_Nang_Anak')
@login_required
def akoa_nang_anak():
    data = {
        "audio_file": "Akoa_Nang_Anak.webm",
        "audio_file2": "Akoa_Nang_Anak2.webm",
        "cebuano_text": "Akoa Nang Anak",
        "english_text": "That is my child",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Akoa_Nang_Inahan')
@login_required
def akoa_nang_inahan():
    data = {
        "audio_file": "Akoa_Nang_Inahan.webm",
        "audio_file2": "Akoa_Nang_Inahan2.webm",
        "cebuano_text": "Akoa Nang Inahan",
        "english_text": "That is my mother",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Iyaha_Ning_Bana')
@login_required
def iyaha_ning_bana():
    data = {
        "audio_file": "Iyaha_Ning_Bana.webm",
        "audio_file2": "Iyaha_Ning_Bana2.webm",
        "cebuano_text": "Iyaha Ning Bana",
        "english_text": "This is his/her husband",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Siya_Ang_Akoang_Asawa')
@login_required
def siya_ang_akoang_asawa():
    data = {
        "audio_file": "Siya_Ang_Akoang_Asawa.webm",
        "audio_file2": "Siya_Ang_Akoang_Asawa2.webm",
        "cebuano_text": "Siya Ang Akoang Asawa",
        "english_text": "She is my wife",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/Sila_Akoang_Mga_Anak')
@login_required
def sila_akoang_mga_anak():
    data = {
        "audio_file": "Sila_Akoang_Mga_Anak.webm",
        "audio_file2": "Sila_Akoang_Mga_Anak2.webm",
        "cebuano_text": "Sila Akoang Mga Anak",
        "english_text": "They are my children",
        "back_url": "/basicBack"
    }
    user = loadJson(session.get('username'))
    progress_data = user.get('progress', {})

    completed = []
    not_completed = []

    for phrase in syllable_map.keys():
        progress_string = progress_data.get(phrase)

        if progress_string and "2" not in progress_string:
            completed.append(phrase)
        else:
            not_completed.append(phrase)
    return render_template('tutor_template.html', **data, completed=completed, not_completed=not_completed)

@app.route('/load', methods=['POST'])
@login_required
def load_data():
    data = loadJson(session.get('username'))
    phrase = request.form.get('phrase', '')
    if phrase:
            syllables = syllable_map.get(phrase, [])
            colorCode = data.get('progress', {}).get(phrase, '')
            return jsonify({
                "syllables": syllables,
                "colorCode": colorCode
            })
    return 'No phrase', 404

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

    filename = f"{page_name}99m.webm" # add gender here
    filepath = os.path.join(user_folder, filename)
    file.save(filepath)
    logger.info(f"Data by user [{name}] saved: {filepath}")
    
    # Insert model response maker script code here
    try:
        subprocess.run(f"./run.sh {name} {filepath}", check=True, shell=True)
        print("Shell script executed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        return f"Error running script: {e}", 500
    
    # RESULT FILE SHOULD BE {user}_result.txt or any way to specify responses to correct user, to be corrected
    result_file = os.path.join('results/', f"{name}_{page_name}.txt") 
    print(result_file)
    try:
        with open(result_file, 'r') as f:
            lines = f.readlines()
            if len(lines) < 4:
                return 'Incomplete result file', 500

            color_code = lines[0].strip()                       
            output_text = lines[1].strip()              
            expected_stress = lines[2].strip() 
            received_stress = lines[3].strip()  
            attempts = int(lines[4].strip())               
            # print(f"Color code: {color_code}, Output text: {output_text}, Expected stress: {expected_stress}, Received stress: {received_stress}, Attempts: {attempts}")
    except FileNotFoundError:
        return 'Result file not found', 500
    
    syllables = syllable_map.get(page_name, [])

    # Update user JSON
    updateProgress(name, page_name, color_code)
    logger.info(f"User [{name}] progress updated.")
    
    return jsonify({
        "message": "Audio uploaded and script executed successfully",
        "color_code": color_code,
        "output_text": output_text,
        "expected_stress": expected_stress,
        "received_stress": received_stress,
        "attempts": attempts,
        "syllables": syllables
    })

# ?
@app.route('/processed_audio/<filename>')
def processed_audio(filename):
    return send_from_directory('processed_audio', filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
