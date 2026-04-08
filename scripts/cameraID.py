from picamera2 import Picamera2
import requests
import time
import cv2
import socket

# --- Load configuration ---
def load_config():
    config = {}

    try:
        with open("camera_config.txt", "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=")
                    config[key] = value
    except FileNotFoundError:
        print("camera_config.txt not found. Using defaults.")

    camera_id = config.get("camera_id", socket.gethostname())
    server_ip = config.get("server_ip", "127.0.0.1")

    server_url = f"http://{server_ip}:8000"

    return camera_id, server_url


CAMERA_ID, SERVER_URL = load_config()


def start_cam(size):
    cam = Picamera2()
    camera_config = cam.create_still_configuration(main={"size": size})
    cam.configure(camera_config)
    cam.start()
    return cam


def capture_img(cam):
    """
    Capture image from Picamera2.
    """
    arr = cam.capture_array("main")
    img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    return img


def convert_jpeg(img):
    """
    Convert cv2 image to JPEG bytes.
    """
    encoded_img = cv2.imencode(".jpg", img)[1]
    return encoded_img.tobytes()


def send_image(img):
    """
    Send the JPEG to the HTTP server with camera ID.
    """
    try:
        response = requests.post(
            SERVER_URL,
            data=img,
            headers={
                "Content-Type": "image/jpeg",
                "Camera-ID": CAMERA_ID
            },
            timeout=5
        )

        if response.status_code != 200:
            print(f"Server responded with status: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")


def main(cam, frequency):
    period = 1 / frequency

    print(f"Camera ID: {CAMERA_ID}")
    print(f"Sending images to: {SERVER_URL}")

    while True:
        start = time.time()

        img = capture_img(cam)
        img = convert_jpeg(img)
        send_image(img)

        elapsed = time.time() - start
        print(f"Transfer time: {elapsed:.3f} seconds")

        if elapsed < period:
            time.sleep(period - elapsed)


if __name__ == "__main__":
    cam = start_cam((1280, 720))

    try:
        main(cam, 5)  # 5 FPS

    except KeyboardInterrupt:
        print("\nStopping camera...")

    finally:
        cam.stop()
