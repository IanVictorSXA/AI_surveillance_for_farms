import asyncio
import threading
import time
import os
import requests
import cv2
import hailo10
from datetime import datetime
from security_alarm import SecurityAlarm
from img_processing_hailo10 import draw_boxes 

RTSP_URL = "rtsp://localhost:8554/"
# rtsp://DarkKnight.local:8554/<id>
camera_list = "http://localhost:9997/v3/paths/list"
default_frame = cv2.imread("/home/team/Desktop/senior_design/dark_knight_logo_original.jpg")

def get_cameras_list(verbose=False):
    r = requests.get(camera_list)
    cameras = []
    if r.status_code == 200:
        rtsp_clients = r.json().get("items", [])
        if verbose:
            print(f"Retrieved {len(rtsp_clients)} cameras:")
        for cam in rtsp_clients:
            cam_name = cam['name']
            cameras.append(cam_name)
            if verbose:
                print(f"- {cam_name}")

    elif verbose: 
        print(f"Failed to retrieve camera list: {r.status_code}")
    
    return cameras    

def set_up_backend(model="yolo26n2", checks=8, sender="ianvictorsouza20@gmail.com", receiver="ianvictorsouza20@gmail.com", verbose=False):
    sa = SecurityAlarm(verbose=verbose)

    with open("password.txt") as file:
        password = file.readline().strip()

    sa.authenticate(sender, password, receiver)

    model = hailo10.yolo_hailo(model)

    camera.alarm = sa

    camera.model = model
    camera.num_classes = len(model.classes)
    camera.classes = model.classes
    camera.checks = checks

    camera.verbose = verbose

    lora = LoRasender()
    camera.lora = lora

    return True

class camera:
    
    alarm = None # Shared SecurityAlarm instance for sending emails
    model = None # Shared Hailo model instance for inference
    num_classes = 0 # Number of classes in the model, used for managing email intervals
    classes = [] # Class names corresponding to class IDs, used for email content
    lora = None # Shared LoRa sender instance for sending LoRa messages
    checks = 1 # Number of consecutive detections required to trigger an email alert and detections, used to reduce false positives
    quality = 80 # JPEG quality for encoding frames sent in email alerts and dashboard, can be adjusted to balance quality and size of the images
    verbose = False # If True, print detailed logs for debugging and monitoring purposes

    def __init__(self, cam_name, conf_threshold=0.5, interval_email=30, use_lora=False, lora_timer=10, night_mode=False):
        """
        Initialize a camera object that connects to the given RTSP stream, performs inference using the specified model, 
        and sends email alerts and LoRa messages based on detections.
        
        Args:
            cam_name (str): The name or URL of the camera stream. 
                If it starts with "rtsp://", it will be used directly as the stream URL.
                Otherwise, it will be appended to the RTSP_URL base.
            conf_threshold (float, optional): Confidence threshold for detections. Defaults to 0.5.
            interval_email (int, optional): Minimum interval in seconds between email alerts for the same class. Defaults to 30.
            lora (bool, optional): Whether to send LoRa messages based on detections. Defaults to False.
            lora_timer (int, optional): Time in seconds to wait before sending a LoRa SLEEP message after the last detection. Defaults to 10.
            """
        self.running = True
        self.night_mode = night_mode
        self.last_emails = []

        self.use_lora = use_lora
        self.awake = False
        self.lora_timer = lora_timer
        self.start = 0

        self.outputs = []
        self.checkers_count = [0] * self.num_classes
        self.conf_threshold = conf_threshold
        self.interval_email = interval_email

        if cam_name.startswith("rtsp://"):
            self.cam_name = cam_name.split("/")[-1]
            self.url = cam_name
        else:
            self.cam_name = cam_name
            self.url = RTSP_URL + cam_name

        
        self.cap = None
        self.frame_ready = threading.Event()
        self.set_up_cap()
        self.frame_show = default_frame.copy()
        self.frame_inference = default_frame.copy()
        self.frame_bytes = None

        self.read_lock = threading.Lock()
        self.return_lock = threading.Lock()
        
        self.read_thread = threading.Thread(target=self.camera_reader, daemon=True)
        self.detect_thread = threading.Thread(target=self.detection, daemon=True)

        self.read_thread.start()
        self.detect_thread.start()

        if self.verbose:
            print(f"Camera {self.cam_name} initialized")

    def camera_reader(self):
        """Continuously read frames from the camera stream in a separate thread to ensure the latest frame is always available for processing and streaming"""
        raw_frame = None
        while self.running:
            # start_time = time.time()
            with self.read_lock:
                raw_frame = self.cap.grab()
            # print("Grabbed frame in %.2f seconds" % (time.time() - start_time))

            if not raw_frame:
                # # Try to reconnect
                if self.verbose:
                    print("%s Stream lost. Reconnecting..." % (self.cam_name))
                # self.running = False
                self.cap.release()
                self.set_up_cap()

    def detection(self):
        """Continuously perform inference on the latest frame in a separate thread, draw detections, and manage email and LoRa alerts based on the results"""
        while self.running:
            with self.read_lock:
                ret, frame_show = self.cap.retrieve()
                
                if self.night_mode:
                    frame_inference = cv2.cvtColor(frame_show, cv2.COLOR_BGR2GRAY)
                    frame_inference = cv2.cvtColor(frame_inference, cv2.COLOR_GRAY2BGR)
                else:
                    frame_inference = frame_show
                    
            # print("Retrieved frame in %.2f seconds" % (time.time() - start_time))

            if not ret:
                time.sleep(0.01)
            else:    
                if camera.model is not None:
                    outputs, dw, dh, r = self.model.infer(frame_inference , conf_threshold=self.conf_threshold)
                    
                    ids_spotted = self.check_detections(outputs)
                    self.outputs = []
                    for output in outputs:
                        class_id = output["cls_id"]
                        if ids_spotted[class_id]:
                            self.outputs.append(output)

                    draw_boxes(self.outputs, frame_show, self.conf_threshold, dw, dh, r)
                    frame_bytes = cv2.imencode('.jpg', frame_show, [cv2.IMWRITE_JPEG_QUALITY, self.quality])[1].tobytes()

                    if camera.alarm is not None and self.outputs:
                        self.send_email(self.outputs, frame_bytes)
                    
                    if camera.lora is not None and self.use_lora:
                        self.send_lora_message(self.outputs)

                with self.return_lock:
                    self.frame_show = frame_show
                    self.frame_bytes = frame_bytes
                    self.frame_ready.set()
    
    def check_detections(self, outputs):
        """Check if the number of consecutive detections for each class meets the threshold.
        
        args:
            outputs (list): List of detection outputs from the model, where each output is a dictionary containing a "cls_id" key for the class ID of the detection.
            
        returns:
            ids_spotted (list): List of boolean values indicating whether each class has been spotted in the current frame. cld_id is used as the index to set the corresponding value to True.
        """
        ids_spotted = [False] * self.num_classes
        
        for output in outputs:
            class_id = output["cls_id"]
            ids_spotted[class_id] = True

        for class_id in range(self.num_classes):
            if ids_spotted[class_id]:
                if self.checkers_count[class_id] < self.checks:
                    self.checkers_count[class_id] += 1
            else:
                self.checkers_count[class_id] = 0
                ids_spotted[class_id] = False

        return ids_spotted
    
    def send_email(self, outputs, frame_bytes):
        """Send an email alert for each detected class if the minimum interval has passed since the last alert for that class.
        
        args:
            outputs (list): List of detection outputs from the model, where each output is a dictionary containing a "cls_id" key for the class ID of the detection.
            frame_bytes (bytes): The latest frame with detections drawn as bytes.
        """
        for output in outputs:
            class_id = output["cls_id"]

            if len(self.last_emails) < class_id + 1:
                for i in range(len(self.last_emails), class_id + 1):
                    self.last_emails.append(datetime.min)

            now = datetime.now()
            if (now - self.last_emails[class_id]).total_seconds() >= self.interval_email:
                self.last_emails[class_id] = now

                if self.verbose:
                    print(f"{self.cam_name}: Sending email for class {self.classes[class_id]} at {now}")
                
                self.alarm.send_email(frame_bytes, cam_id=self.cam_name, date=now.strftime(r"%m-%d-%Y %H:%M:%S"), class_id=self.classes[class_id])

    def send_lora_message(self, outputs):
        """Send a LoRa AWAKE message if there are detections and the camera is not already awake. Send a LoRa SLEEP message if there have been no detections for a certain amount of time.
        
        args:
            outputs (list): List of detection outputs from the model, where each output is a dictionary containing a "cls_id" key for the class ID of the detection.
        """
        if outputs:
            if not self.awake:
                self.awake = True
                if self.verbose:
                    print(f"{self.cam_name}: Sending LoRa AWAKE signal")
                self.lora.send_message(str(self.cam_name) + "_AWAKE")
            self.start = time.time()
        else:
            if self.awake and ((time.time() - self.start) >= self.lora_timer):
                self.awake = False
                if self.verbose:
                    print(f"{self.cam_name}: Sending LoRa SLEEP signal")
                self.lora.send_message(str(self.cam_name) + "_SLEEP")

    def set_up_cap(self):
        """Set up the video capture for the camera stream, with reconnection logic in case the stream is lost"""
        if self.verbose:
            print("Connecting to camera...")

        while self.running:
            cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                time.sleep(5)
                continue

            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            self.cap = cap

            if self.verbose:
                print(f"Camera {self.cam_name} connected.")
            return
    
    def get_frame_bytes(self):
        """Synchronous wrapper for get_frame - use in Flask and email alerts to get the latest frame bytes for the camera"""
        self.frame_ready.wait()
        self.frame_ready.clear()
        
        with self.return_lock:
            return self.frame_bytes
    
    def get_frame(self):
        """Get the latest frame with detections drawn - use for testing"""
        self.frame_ready.wait()
        self.frame_ready.clear()
        
        with self.return_lock:
            return self.frame_show
        
    def stop(self):
        """Stop the camera reader and detection threads, release the video capture, and send a LoRa SLEEP message if applicable when shutting down the camera"""
        if self.verbose:
            print(f"Stopping camera {self.cam_name}...")

        self.running = False
        self.read_thread.join()
        self.detect_thread.join()

        if self.cap is not None:
            self.cap.release()
        
        if self.awake:
            self.lora.send_message(str(self.cam_name) + "_SLEEP")

class LoRasender:
    def __init__(self):
        """Initialize the LoRa sender by setting up the SPI interface and configuring the RFM9x module for communication"""
        import digitalio
        import board
        import busio
        import adafruit_rfm9x

        RADIO_FREQ_MHZ = 915.0
        CS = digitalio.DigitalInOut(board.CE1)
        RESET = digitalio.DigitalInOut(board.D17)
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        self.rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ, baudrate=115200)
        # self.rfm9x.signal_bandwidth = 125000

    def send_message(self, message):
        """Send a message over LoRa using the RFM9x module. The message is encoded as bytes before being sent."""
        self.rfm9x.send(message.encode())

if __name__ == "__main__":
   
    def main():
        set_up_backend(verbose=True)
        cameras = get_cameras_list()
        print(cameras)

        fps_counter = 0
        start_time = time.time()
        # FPS = 30
        # frame_time = 1.0 / FPS
        frame = None


        cams = []
        for cam_name in cameras:
            print(f"Starting camera reader for {cam_name}")
            if cam_name == "ianRaspPi5":
                cam = camera(cam_name, conf_threshold=0.5, interval_email=15, use_lora=True)
                break
            else:
                cam = camera(cam_name, conf_threshold=0.5, interval_email=15)
            cams.append(cam)

        # cam = cams[1] if len(cams) > 1 else cams[0]

        index = 0
        frame = cam.get_frame()
        print(frame.shape)
        while cam.running:
            now = time.time()

            frame = cam.get_frame()

            fps_counter += 1
            if time.time() - start_time >= 1:
                # print("FPS:", fps_counter)
                fps_counter = 0
                start_time = time.time()

            cv2.imshow("Camera Worker", frame)


            if cv2.waitKey(1) == 27:
                cam.stop()
                camera.model.close()
                # break

        cv2.destroyAllWindows()
    
    main()

