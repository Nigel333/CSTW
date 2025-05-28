# Website functions

from app import db, USERDATA_FOLDER
from pathlib import Path
import bcrypt
import base64
import re
import json
import os

def getID(inc):
    cursor = db.cursor()
    #print(cursor)
    try:
        cursor.execute("SELECT MAX(user_id) FROM web_user")
        #print(cursor)
    except Exception as e:
        print("error somewhere", e)
    #print('Getting ID')
    result = cursor.fetchone()
    if not result[0]:
        return 1
    #print(result[0])
    if inc:
        return result[0]+1
    return result[0]

def newUserCheck(username,email,firstName,lastName,password,confirmPass):
    flag = 0 # If passwords don't match
    if (password == confirmPass and bool(username) and checkEmail(email) 
        and bool(firstName) and bool(lastName)):
        flag = 1  # If new user

    cursor = db.cursor(buffered=True)
    query = "SELECT username, email FROM web_user WHERE username = %s OR email = %s"
    cursor.execute(query, (username, email))
    result = cursor.fetchone()

    if result:
        if result[0] == username or result[1] == email:
            return -1  # Username/Email exists
    
    return flag

def checkEmail(email):
    valid = re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email)
    if valid:
        return 1
    return 0

def insertNewUser(userid, username, firstName, lastName, email, password):
    bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=15,prefix=b'2b')
    hashed = bcrypt.kdf(
        password=bytes,
        salt=salt,
        desired_key_bytes=32,
        rounds=178
    )
    cursor = db.cursor()
    #print("pass: " + str(hashed))
    query = "INSERT INTO web_user (user_id, username, first_name, last_name, email, password, salt) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    cursor.execute(query, (userid, username, firstName, lastName, email, str(hashed), salt))
    db.commit()

def checkLogin(username, password):
    if password == "":
        return [username,-1] # invalid login
    
    cursor = db.cursor()
    query = "SELECT * FROM web_user WHERE username = %s"
    cursor.execute(query,[username])
    result = cursor.fetchone()
    if result:
        hashed = bcrypt.kdf(
            password=password.encode('utf-8'),
            salt=result[6].encode('utf-8'),
            desired_key_bytes=32,
            rounds=178
        )
        #print(result[5].encode('utf-8'))
        #print(password.encode('utf-8'))
        if str(hashed)==str(result[5]):
            return [username,1]
        
    return [username,-1] # invalid login

def retrieveData(username):
    if username is None:
        return None
    
    #print("retrieve: "+ username)
    cursor = db.cursor()
    query = "SELECT * FROM web_user WHERE username = %s"
    cursor.execute(query,[username])
    result = cursor.fetchone()
    
    if result is None:
        return None
    
    return {
        "user_id": result[0],
        "username": result[1],
        "first_name": result[2],
        "last_name": result[3],
        "email": result[4],
    }
    

# Json functions

# Get file path 
def getJsonPath(username):
    # Sanitize username for safe filename
    safe_username = "".join(c for c in username if c.isalnum() or c in "._-")
    return os.path.join(USERDATA_FOLDER, f"{safe_username}.json")

# Load user data
def loadJson(username):
    file_path = getJsonPath(username)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    
    # Return default structure if file doesn't exist
    return {
        "user": username,
        "progress": {}
    }

# Save user data
def saveJsonData(username, data):
    file_path = getJsonPath(username)

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Update progress
def updateProgress(username, word, score):
    data = loadJson(username)
    data["progress"][word] = score
    saveJsonData(username, data)
    return data