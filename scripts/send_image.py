import subprocess
import requests
import time
import cv2

SERVER_URL = "http://192.168.1.102:8000/upload" # Remember to change this
TEMP = "results/wildHog1007.jpg" # Change this

def capture_image():
    """
    Capture image using rpicam-jpeg.
    """
    print("Capturing image...")
    cmd = [
        "rpicam-jpeg",
        "-o", TEMP,
        "-t", "1",
        "--width", "1280",
        "--height", "720",
        "--quality", "90"
    ]
    subprocess.run(cmd, check=True)
    # print("Raw capture complete.")

def clean_exif():
    """
    Remove EXIF metadata to ensure PC compatibility.
    """
    # print("Stripping EXIF metadata...")

    img = cv2.imread(TEMP)

    # Encode to JPEG
    encoded_img = cv2.imencode(".jpg", img)[1]
    img = encoded_img.tobytes()
    return img

def send_image(img):
    """
    Send the cleaned JPEG to the HTTP server.
    """
    # print("Sending image to server...")
    response = requests.post(SERVER_URL, data=img, headers={"Content-Type": "image/jpeg"})
    # print(f"Server response: {response.text}")

def main(frequency):
    period = 1 / frequency
    while True:
        start = time.time()
        img = clean_exif()
        send_image(img)
        elapsed = time.time() - start
        print(f"Transfer time: {elapsed:.3f} seconds")
        if elapsed < period:
            time.sleep(period - elapsed)


if __name__ == "__main__":
    main(1)