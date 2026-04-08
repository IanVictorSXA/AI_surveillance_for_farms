# makes a server and save all pictures received
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
        length = int(self.headers['Content-Length'])
        data = self.rfile.read(length)
        arr = np.fromstring(data, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        
        os.makedirs(SAVE_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S_%f")
        filename = os.path.join(SAVE_DIR, f"image{timestamp}.jpg")

        cv2.imwrite(filename, frame)

        print(f"[OK] Image received → {filename}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"received")

with socketserver.TCPServer(("", PORT), ImageHandler) as httpd:
    print(f"Listening on port {PORT}... Waiting for images.")
    httpd.serve_forever()
