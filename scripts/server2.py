# HTTP server that receives images and saves them organized by camera ID

import http.server
import socketserver
import os
from datetime import datetime
import cv2
import numpy as np

PORT = 8000
SAVE_DIR = "received_images"


class ImageHandler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):

        # Get camera ID from header (default if missing)
        camera_id = self.headers.get("Camera-ID", "UNKNOWN_CAMERA")

        # Read image bytes
        length = int(self.headers['Content-Length'])
        data = self.rfile.read(length)

        # Convert bytes → OpenCV image
        arr = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if frame is None:
            print("[ERROR] Failed to decode image")
            self.send_response(400)
            self.end_headers()
            return

        # Create folder for this camera
        camera_dir = os.path.join(SAVE_DIR, camera_id)
        os.makedirs(camera_dir, exist_ok=True)

        # Create timestamp filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(camera_dir, f"image_{timestamp}.jpg")

        # Save image
        cv2.imwrite(filename, frame)

        print(f"[OK] Image received from {camera_id} → {filename}")

        # Send response
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"received")


with socketserver.TCPServer(("", PORT), ImageHandler) as httpd:
    print(f"Listening on port {PORT}... Waiting for images.")
    httpd.serve_forever()

