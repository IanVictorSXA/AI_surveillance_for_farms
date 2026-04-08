import threading
import time
import os
import requests

RTSP_URL = "rtsp://localhost:8554/"
# rtsp://DarkKnight.local:8554/<id>

r = requests.get("http://localhost:9997/v3/paths/list")
print(r.json())
name = r.json()["items"][0]["name"]

# ==============================
# Enable FFmpeg HW decoding hints
# ==============================

# Linux (Raspberry Pi / Intel iGPU)
# os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
#     "rtsp_transport;tcp|"
#     "fflags;nobuffer|"
#     "flags;low_delay|"
#     "hwaccel;auto"
# )

# Windows NVIDIA example (uncomment if NVIDIA GPU)
# os.environ[""OPENCV_FFMPEG_CAPTURE_OPTIONS""] = (
#     ""rtsp_transport;tcp|hwaccel;cuda|video_codec;h264_cuvid""
# )

# ==============================

import cv2 as cv

caps = {}
pos = {"cap": 0,
       "lock": 1}
running = True


# -------------------------------------------------
# Camera reader thread
# -------------------------------------------------

def set_up_thread(cam_name):
    # print("set up thread: ", cam_name)
    caps[cam_name] = [None, threading.Lock()]

def set_up_cap(url, cam_name):
    print("Connecting to camera...")

    while True:
        cap = cv.VideoCapture(url, cv.CAP_FFMPEG)
        if not cap.isOpened():
            time.sleep(2)
            continue

        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
        
        # minimal buffering → lowest latency
        caps[cam_name][pos["cap"]] = cap

        print("Camera connected.")
        return cap
    
def camera_reader(cam_name):
    url = RTSP_URL + cam_name    
    
    set_up_thread(cam_name)
    cap = set_up_cap(url, cam_name)
    
    lock = caps[cam_name][pos["lock"]]
    raw_frame = None

    while running:

        with lock:
            raw_frame = cap.grab()

        if not raw_frame:
            # # Try to reconnect
            print("%s Stream lost. Reconnecting..." % (cam_name))
            cap.release()
            cap = set_up_cap(url, cam_name)


def start_thread(cam_name):
    threading.Thread(target=camera_reader, daemon=True, kwargs=dict(cam_name=cam_name)).start()
    
        # cap.release()
        # time.sleep(1)


# -------------------------------------------------
# Start reader thread
# -------------------------------------------------

start_thread(name)

# -------------------------------------------------
# Main processing loop
# -------------------------------------------------
fps_counter = 0
start_time = time.time()
FPS = 30
frame_time = 1.0 / FPS
last_time = 0
frame = None
ret = True

from hailo10 import yolo_hailo
model_path = "models/yolo26n_mkIII_Radam_960_150_nms.hef"
input_shape = (960, 960)
outputs = ("conv61",
           "conv64",
           "conv77",
           "conv80",
           "conv91",
           "conv94")  # The output layer(s) to be retrieved after inference

model = yolo_hailo(model_path, outputs, input_shape)

while not caps[name][pos["cap"]]:
    time.sleep(1)

print(caps[name])
while True:
    now = time.time()

    with caps[name][pos["lock"]]:
        ret, frame = caps[name][pos["cap"]].retrieve()


    fps_counter += 1
    if time.time() - start_time >= 1:
        print("FPS:", fps_counter)
        fps_counter = 0
        start_time = time.time()
    
    if frame is None or not ret:
        time.sleep(0.01)
        continue
    
    # if now - last_time < frame_time:
    #     time.sleep(0.001)
    #     continue

    last_time = now
    

    # outputs, frame = model.infer(frame, conf_threshold=0.5) 
    # print(outputs)

    cv.imshow("Camera Worker", frame)


    if cv.waitKey(1) == 27:
        running = False
        # model.close()
        break

cv.destroyAllWindows()
