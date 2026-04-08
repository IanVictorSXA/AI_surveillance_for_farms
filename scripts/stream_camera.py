# Based on https://github.com/EbenKouao/pi-camera-stream-flask/blob/master/main.py
#Desc: This web application serves a motion JPEG stream
# import the necessary packages
from flask import Flask, render_template, Response, request, send_from_directory
import os
import scripts.img_processing_hailo8 as processing
import time
import _thread
import http.server
import socketserver
import os
from datetime import datetime
import cv2
import numpy as np

PORT = 8000
model_name = "yolov11x_mkII"
model_folder_path = "models"
model = processing.Model(model_name=model_name, folder_path=model_folder_path)
frame = cv2.imread("dark_knight_logo.jpg")

class ImageHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        global frame
        length = int(self.headers['Content-Length'])
        data = self.rfile.read(length)
        arr = np.fromstring(data, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        
        # os.makedirs(SAVE_DIR, exist_ok=True)

        # timestamp = datetime.now().strftime("%Y%m%d%H%M%S_%f")
        # filename = os.path.join(SAVE_DIR, f"image{timestamp}.jpg")

        # cv2.imwrite(filename, frame)

        print(f"[OK] Image received")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"received")

# App Globals (do not edit)
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html') #you can customize index.html here

def gen(model):
    #get camera frame
    while True:        
        frame_inferred = model.infer(frame)
        ret, jpeg = cv2.imencode(".jpg", frame_inferred)
        # print("ENCODE:", ret, len(jpeg))
        time.sleep(1)
        jpeg_bytes = jpeg.tobytes()
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Content-Length: ' + f"{len(jpeg_bytes)}".encode() + b'\r\n'
            b'\r\n' + 
            jpeg_bytes + 
            b'\r\n'
            )

@app.route('/video_feed')
def video_feed():
    return Response(gen(model),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Take a photo when pressing camera button
# @app.route('/picture')
# def take_picture():
#     pi_camera.take_picture()
#     return "None"

if __name__ == '__main__':
    _thread.start_new_thread(app.run, (), {"host":'0.0.0.0', "debug":False})
    with socketserver.TCPServer(("", PORT), ImageHandler) as httpd:
        print(f"Listening on port {PORT}... Waiting for images.")
        httpd.serve_forever()
    


