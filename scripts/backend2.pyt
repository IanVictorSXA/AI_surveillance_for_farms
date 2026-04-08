import cv2 as cv
import threading
import time
import os

RTSP_URL = "rtsp://localhost:8554/mystream"

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

thread_data = {}
pos = {"lock": 0,
       "frame": 1}
running = True


# -------------------------------------------------
# Camera reader thread
# -------------------------------------------------

def set_up_thread(url):
    cam_name = url.split("/")[-1]
    thread_data[cam_name] = [threading.Lock(), None]

    return cam_name

def set_up_cap(url, name):
    print("Connecting to camera...")

    while True:
        cap = cv.VideoCapture(url, cv.CAP_FFMPEG)
        if not cap.isOpened():
            time.sleep(2)
            continue

        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
        
        # minimal buffering → lowest latency

        print("Camera connected.")
        return cap
    
def camera_reader(RTSP_URL):
    name = set_up_thread(RTSP_URL)
    
    cap = set_up_cap(RTSP_URL, name)
    
    lock, frame = thread_data[name]

    while True:

        if not cap.grab():
            # # Try to reconnect
            print("%s Stream lost. Reconnecting..." % (name))
            cap.release()
            cap = set_up_cap(RTSP_URL, name)

        ret, frame = cap.retrieve()

        if not ret:
            continue

        with lock:
            thread_data[name][pos["frame"]] = frame
            


def start_thread(RTSP_URL):
    threading.Thread(target=camera_reader, daemon=True, kwargs=dict(RTSP_URL=RTSP_URL)).start()
    
        # cap.release()
        # time.sleep(1)


# -------------------------------------------------
# Start reader thread
# -------------------------------------------------

start_thread(RTSP_URL)

# -------------------------------------------------
# Main processing loop
# -------------------------------------------------
fps_counter = 0
start_time = time.time()
FPS = 30
frame_time = 1.0 / FPS
last_time = 0
frame = None

while thread_data["mystream"][pos["frame"]] is None:
    time.sleep(1)

while True:
    now = time.time()

    with thread_data["mystream"][pos["lock"]]:
        frame = thread_data["mystream"][pos["frame"]].copy()


    
    if frame is None:
        time.sleep(0.01)
        continue
    
    if now - last_time < frame_time:
        time.sleep(0.001)
        continue

    fps_counter += 1
    if time.time() - start_time >= 1:
        print("FPS:", fps_counter)
        fps_counter = 0
        start_time = time.time()
    
    last_time = now

    cv.imshow("Camera Worker", frame)


    if cv.waitKey(1) == 27:
        running = False
        break

cv.destroyAllWindows()