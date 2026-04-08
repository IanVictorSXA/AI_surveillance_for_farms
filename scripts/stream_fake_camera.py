# Based on https://github.com/EbenKouao/pi-camera-stream-flask/blob/master/main.py
#Desc: This web application serves a motion JPEG stream
# import the necessary packages
from flask import Flask, render_template, Response, request, send_from_directory
import os
import scripts.img_processing_hailo8 as processing
import time

folder = "data"
img_names = processing.get_img_names(folder)
camera = processing.Simulate_Camera(img_names, folder)
model_name = "yolov11x_mkII"
model_folder_path = "models"
model = processing.Model(model_name=model_name, folder_path=model_folder_path)

# App Globals (do not edit)
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html') #you can customize index.html here

def gen(camera, model):
    #get camera frame
    while True:
        frame = camera.get_cv_frame()
        frame = model.infer(frame)
        frame = camera.cv_to_jpeg(frame)
        time.sleep(1)
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Content-Length: ' + f"{len(frame)}".encode() + b'\r\n'
            b'\r\n' + 
            frame + 
            b'\r\n'
            )

@app.route('/video_feed')
def video_feed():
    return Response(gen(camera, model),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Take a photo when pressing camera button
# @app.route('/picture')
# def take_picture():
#     pi_camera.take_picture()
#     return "None"

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)