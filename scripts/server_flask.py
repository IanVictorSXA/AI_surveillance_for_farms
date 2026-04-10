# Flask Backend Setup for Security Camera Monitor
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import cv2
import uuid
import json
import os
from datetime import datetime
import threading
import backend as bk

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend
cameras = {}
cam_with_lora = "cam1"  # Example camera ID that has LoRa integration
cam_night_mode = "cam10"  # Example camera ID that has night mode enabled
# In-memory database (replace with SQLite or PostgreSQL for production)
def setup_cams():
    global cameras
    cameras_list = bk.get_cameras_list()

    if not cameras:
        for cam in cameras_list:
            cameras[cam] = bk.camera(cam, use_lora=True if cam == cam_with_lora else False, night_mode= True if cam == cam_night_mode else False)
    
    if cameras:
        for cam in cameras.copy().keys():
            if cam not in cameras_list:
                cameras[cam].stop()
                del cameras[cam]
                
        for cam in cameras_list:
            if cam not in cameras:
                cameras[cam] = bk.camera(cam, use_lora=True if cam == cam_with_lora else False)
                    
# Configuration file to persist cameras
# CONFIG_FILE = 'cameras_config.json'

# def load_cameras():
#     """Load cameras from config file on startup"""
#     global cameras
#     if os.path.exists(CONFIG_FILE):
#         with open(CONFIG_FILE, 'r') as f:
#             cameras = json.load(f)
#             print(f"Loaded {len(cameras)} cameras from config")

# def save_cameras():
#     """Save cameras to config file"""
#     with open(CONFIG_FILE, 'w') as f:
#         json.dump(cameras, f, indent=2)

def generate_frames(camera_id):
    """Generate video frames from camera stream"""
    
    cam = cameras.get(camera_id, None)
    if not cam:
        return
    
    while True:
        img_bytes  = cam.get_frame_bytes()       
        
        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + img_bytes + b'\r\n')

@app.route('/cameras', methods=['GET'])
def get_cameras():
    """Get all cameras"""
    setup_cams()

    to_send = [{"id": cam_id, "location": cam_id} for cam_id, cam in cameras.items()]

    return jsonify(to_send)

@app.route('/cameras', methods=['POST'])
def add_camera():
    """Add a new camera"""
    data = request.json
    location = data.get('location')
    stream_url = data.get('streamUrl')
    
    if not location or not stream_url:
        return jsonify({'error': 'Location and streamUrl are required'}), 400
    
    new_camera = {
        'id': str(uuid.uuid4()),
        'location': location,
        'streamUrl': stream_url,
        'addedAt': datetime.now().isoformat()
    }
    
    cameras.append(new_camera)
    # save_cameras()
    
    return jsonify(new_camera), 201

@app.route('/cameras/<camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    """Delete a camera"""
    global cameras
    
    # Release video capture if exists
    if camera_id in cameras:
        cameras[camera_id].stop()
        del cameras[camera_id]
    # save_cameras()
    
    return jsonify({'success': True})

@app.route('/video_feed/<camera_id>')
def video_feed(camera_id):
    """Video streaming route"""
    return Response(
        generate_frames(camera_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'cameras_count': len(cameras),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    bk.set_up_backend(checks=1)
    setup_cams()
    
    print("=" * 50)
    print("Security Camera Monitor - Flask Backend")
    print("=" * 50)
    print(f"Loaded {len(cameras)} cameras")
    print("Server running on http://localhost:5000")
    print("=" * 50)
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
