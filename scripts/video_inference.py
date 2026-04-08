import scripts.img_processing_hailo8 as img_processing_hailo8
import cv2
import os
import time

path_video = "videos/wildBoar.mp4"
output_folder = "video_outputs"
character_coding = "XVID"

threshold = 0.7
model_name = "yolov11x_mkII"
path, filename = os.path.split(path_video)
name, ext = os.path.splitext(filename)
name += "_" + model_name
ext = ".avi"
output_path = os.path.join(output_folder, name + ext)

fps = 30
frame_size = (1920, 1080)
isColor = True # False for grayscale video
cap = cv2.VideoCapture(path_video)

if cap.isOpened():
    print("Video file opened successfuly!")
else:
    print("Error: could not find file.")
    exit()

fourcc = cv2.VideoWriter.fourcc(*character_coding)
out = cv2.VideoWriter(output_path, fourcc, fps, frame_size) 

model = img_processing_hailo8.Model(model_name=model_name, threshold=threshold)

start = time.time()
skip_frames = 1
frame_pos = 0
while True:
    ret, frame = cap.read()
    if not ret:
        print("End of video.")
        break
    frame_infered = model.infer(frame)
    out.write(frame_infered)
print("Time elapsed: {}".format(time.time() - start))

cap.release()
out.release()
