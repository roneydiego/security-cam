from flask import Flask, render_template, Response, request
import cv2
from datetime import datetime

from requests import get
from time import localtime, sleep
from os import makedirs, getcwd
import threading

import RPi.GPIO as GPIO

#this code was made to run on a raspberry pi with a servo motor connected to it
#This code will run on your local network

GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.OUT)
servo1 = GPIO.PWM(11, 50)
servo1.start(0)
duty = 7
    
app = Flask(__name__)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 24.0)

font = cv2.FONT_HERSHEY_PLAIN
vidWidth = 640
vidHeight = 480

wd = getcwd()
net = cv2.dnn.readNetFromCaffe(f'{wd}/MobileNetSSD_deploy.prototxt', f'{wd}/SSD_MobileNet.caffemodel')
pessoa_index = 15
#this is the token you get once you create a telegram bot
TOKEN = ''

#this is where you should paste your telegram ID, it's an integer
meuid = 0


def enviar_foto(path, caption):
    with open(path, 'rb') as o:
        foto = {'photo':o}
        get(f'https://api.telegram.org/bot{TOKEN}/sendPhoto?chat_id={meuid}&caption={caption}', files=foto)



    
def person_detector(img):
    try: 
        quantidade_de_pessoas = 0
        height, width = img.shape[0:2]

        blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 0.007, (300, 300), 130)
        net.setInput(blob)
        detected = net.forward()
        all_confidence = 0
        
        for i in range(detected.shape[2]):
            tipo_de_obj = detected[0][0][i][1]
            confidence = detected[0][0][i][2]
            if tipo_de_obj == pessoa_index and confidence>=0.1:
                all_confidence += confidence
                quantidade_de_pessoas += 1

        if quantidade_de_pessoas > 0:
            ano, mes, dia, hora, minutos, segundos = localtime()[:6]
            hora_detection = f'{hora}:{minutos}:{segundos}'
            nome_arquivo = f'{dia}-{mes}-{ano}_{hora}-{minutos}-{segundos}'
            avg_confidence = all_confidence/quantidade_de_pessoas
            
            path = f'{wd}/{ano}/detected_people'
            try:
                makedirs(path)
            except FileExistsError:
                pass
            
            cv2.imwrite(f'{path}/{nome_arquivo}.jpg', img)
            thread = threading.Thread(target=enviar_foto, args=(f'{path}/{nome_arquivo}.jpg', f'{quantidade_de_pessoas} pessoa(s) detectada(s)\nHorário: {hora_detection}\nConfiança: {round(avg_confidence*100, 2)}%'
    ))
            thread.start()
            return True
        else:
            return False
    except:
        return False


def path_creator():
    import os 
    from datetime import date, datetime
    months = ['JAN', 'FEV', 'MARC', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
    
    now_info = datetime.now()
    year = now_info.year
    monthindex = now_info.month

    dataCompleta = date.today()
    
    wd = os.getcwd()

    path = f'{wd}/{year}/{months[monthindex-1]}/{dataCompleta}'
    path2 = f'{wd}/{year}/{months[monthindex-1]}'
    try:
        os.makedirs(path)
    except FileExistsError:
        pass
    else:
        try:
            pasta_dias = os.listdir(path2)
            print(pasta_dias)
            new_path = fr'{path2}/{pasta_dias[1]}'
            files = os.listdir(new_path)
        except Exception as e:
            print(e)
            pass

        try:
            for f in files:
                os.system(f'rm {new_path}/{f}')
        except Exception as b:
            print(b)
            pass
        finally:
            if len(pasta_dias) > 1:
                os.rmdir(new_path)

    return path

framesForStream = None
framesForDetector = None
def cam():
    from time import time
    global framesForStream
    global framesForDetector
    while True:
        path = path_creator()
        ano, mes, dia, hora, minutos, segundos = localtime()[:6]
        filename = f'{dia}-{mes}-{ano}_{hora}-{minutos}-{segundos}'
        
        writer = cv2.VideoWriter(f'{path}/{filename}.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 24.0, (vidWidth, vidHeight))
        start_time = time()
        while time() - start_time < 10*60:
            ok, ogFrame = cap.read()
            if ok:    
                cv2.putText(ogFrame, str(datetime.now())[:-7], (20, 40), font, 2, (255, 255, 255), 2, cv2.LINE_AA)
                writer.write(ogFrame)
                
                framesForStream = ogFrame
                framesForDetector = ogFrame
        print(f'[{str(datetime.now())[:-7]}] Gravação completa')
        writer.release()
thread = threading.Thread(target=cam)
thread.start()

enable_person_detec_var = False
def use_person_detector():
    from time import sleep
    global enable_person_detec_var
    global framesForDetector
    global state_person_detec 
    while True:
        if localtime()[3] < 6:
            detected = person_detector(framesForDetector)
            if detected:
                #leitor()
                sleep(60)
        elif enable_person_detec_var:
            detected = person_detector(framesForDetector)
            if detected:
                sleep(60)
thread3 = threading.Thread(target=use_person_detector)
thread3.start()

def servo(duty):
    servo1.ChangeDutyCycle(duty)
    sleep(0.1)
    servo1.ChangeDutyCycle(0)


def stream():
    global framesForStream
    while True:       
        try:
            trash, frame = cv2.imencode('.jpeg', framesForStream)
            frame = frame.tobytes()                
        except:
            pass
        yield (b' --frame\r\n' b'Content-type: image/jpeg\r\n\r\n' + frame + b'\r\n')
@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/video')
def video():
    return Response(stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/', methods=['GET', 'POST'])
def bu():
    global duty
    global enable_person_detec_var
    state = 'Disabled'
    if request.method == 'POST':
        if request.form.get('<') == '<':
            servo(duty - 0.5)
            duty -= 0.5
            if duty < 2:
                duty = 2    
        elif request.form.get('>') == '>':
            servo(duty + 0.5)
            duty += 0.5
            if duty > 12:
                duty = 12

        elif request.form.get('center') == 'center':
            duty = 7
            servo(7)
        elif request.form.get('Enable') == 'True':
            enable_person_detec_var = True
            state = 'Enabled'
        elif request.form.get('Disable') == 'False':
            state = 'Disabled'
            enable_person_detec_var = False
        
    return render_template('index.html', files=state)   
        


app.run('0.0.0.0', port='5000', debug=False)
	
