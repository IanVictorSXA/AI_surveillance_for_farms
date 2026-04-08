# Desc: functions for processing images (letterbox, draw bounding box, read images, save images to folder,
#  simulate a camera by using a folder of images)

import cv2
import numpy as np
import os

colors = ((0,0,255), (255,0,0), (0,255,0))
animals = ("coyote", "fox", "feral hog")
black = (0, 0, 0)
text_thickness = 2
text_scale = 0.75

def letterbox(img : str | cv2.typing.MatLike, new_shape : tuple[int, int]=(640, 640), color=(114, 114, 114)) -> tuple[cv2.typing.MatLike, float, float]:
    """Takes in an image and reshape it to the desired shape while keeping aspect ratio, and pads with pixels of desired color to reach new size
    Params:
        img : path to image or image object (E.g.: returned object by cv2.imread)
        new_shape: new resolution. Defaults to (640, 640).
        color: color of padding pixels in BGR format. Defaults to gray.
        
    Returns: a new image object in RGB format (cv2.Mat)"""
    # Based on ultralytics code

    if type(img) == str:
        _img = cv2.imread(img)
    else:
        _img = img.copy()

    shape = _img.shape[:2]  # current shape [height, width]
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    new_unpad = (int(shape[1] * r), int(shape[0] * r))

    dw = new_shape[1] - new_unpad[0]
    dh = new_shape[0] - new_unpad[1]
    dw /= 2
    dh /= 2

    _img = cv2.resize(_img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))

    _img = cv2.copyMakeBorder(
        _img, top, bottom, left, right,
        cv2.BORDER_CONSTANT, value=color
    )
    
    _img = cv2.cvtColor(_img, cv2.COLOR_BGR2RGB)

    return _img, dw, dh, r

def get_dataset(image_folder : str) -> tuple[np.ndarray[cv2.typing.MatLike], np.ndarray[str]]:
    """Takes in path to folder of pictures and returns a 2-tuple.
      First item is an array of image objects. Second is an array of the name of each image file."""
    
    image_names = get_img_names(image_folder)
    dataset = np.zeros((len(image_names), 640, 640, 3), dtype=(np.float32))

    for idx, img_name in enumerate(image_names):
        img_path = os.path.join(image_folder, img_name)
        img_letterboxed = letterbox(img_path)
        dataset[idx, :, :, :] = img_letterboxed
    
    return dataset, image_names

def get_img_names(image_folder : str) -> np.ndarray[str]:
    """Takes in a folder of images. Returns array of file name of each picture."""
    image_names = np.array([img_name for img_name in os.listdir(image_folder) if os.path.splitext(img_name)[1] == ".jpg"]) 
    
    return image_names

def undo_letterbox(xmin, ymin, xmax, ymax, dw, dh, r):
    xmin = (xmin - round(dw - 0.1)) / r
    ymin = (ymin - round(dh - 0.1)) / r
    xmax = (xmax - round(dw + 0.1)) / r
    ymax = (ymax - round(dh + 0.1)) / r

    return int(xmin), int(ymin), int(xmax), int(ymax)


def draw_boxes(result : np.ndarray[np.float64], img : cv2.typing.MatLike, threshold : float, dw=0, dh=0, r=1) -> cv2.typing.MatLike:
    """Draws bounding boxes on an image based on detection results.

    Params: 
        result: array result of a single image returned by hailo's infer function (hailo.py)
        img: original image object
        shape: shape of image object
        threshold:  draw box if confidence is >= threshold
    """
    # based on https://github.com/EdjeElectronics/Train-and-Deploy-YOLO-Models/blob/main/yolo_detect.py
    
    # for i, animal_arr in enumerate(result): # loop through each animal class array. i is the animal class
    for detection in result: # detection = [ymin, xmin, ymax, xmax, confidence]
        confidence = detection["conf"]
        if confidence >= threshold:
            xmin = int(detection["x1"]) #* model_input[1]) 
            ymin = int(detection["y1"])# * model_input[0])
            xmax = int(detection["x2"]) # * model_input[1])
            ymax = int(detection["y2"])# * model_input[0])
            i = detection["cls_id"] # class id
            color = colors[i]
            xmin, ymin, xmax, ymax = undo_letterbox(xmin, ymin, xmax, ymax, dw, dh, r)

            # label = f'{animals[i]}: {int(confidence*100)}%'
            label = f'{animals[i]}: {int(confidence*100)}%'
            labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, text_scale, text_thickness) # Get font size
            label_ymin = max(ymin, labelSize[1] + 10) # Make sure not to draw label too close to top of window
            
            cv2.rectangle(img, (xmin, label_ymin-labelSize[1]-10), (xmin+labelSize[0], label_ymin+baseLine-10), color, cv2.FILLED) # Draw box to put label text in
            cv2.putText(img, label, (xmin, label_ymin-7), cv2.FONT_HERSHEY_SIMPLEX, text_scale, black, text_thickness) # Draw label text
            cv2.rectangle(img, (xmin, ymin), (xmax, ymax), color, thickness=2) # bounding box


def save_results(results : np.ndarray[np.float64], image_names : np.ndarray[str], image_folder : str, destination_folder : str) -> None:
    """Saves images with bounding boxes to folder.
    
    Params:
        results: results given by hailo inference (hailo.py Hailo_Device.infer)
        images_names: numpy array of names of the image files
        image_folder: folder path to images
        destination_folder: folder path to save results.

    Returns: None
    """
    for idx, img_name in enumerate(image_names):
        result = results[idx] # get data for each picture
        img_path = os.path.join(image_folder, img_name)
        img = letterbox(img_path)[0]
        img = draw_boxes(result, img)
        destination = os.path.join(destination_folder, img_name)
        save_img(img, destination)

def save_img(img : cv2.typing.MatLike, destination : str) -> None:
    """Saves a single image.
    
    Params:
        img: image object.
        destination: destination folder"""
    cv2.imwrite(destination, img)

class Simulate_Camera:
    # To return one image at a time from a folder
    def __init__(self, img_names, img_dir, file_type="jpg"):
        """Saves image file names and image folder to simulate a camera returning a frame 
        
        Params:
            img_names: image file names
            img_dir: image folder path
            file_type: images file type. Defaults to "jpg" """
        
        self.img_dir = img_dir
        self.img_names = img_names
        self.size = img_names.shape[0]
        self.index = -1
        self.file_type = "." + file_type

    def get_jpeg_frame(self)  -> bytes:
        """ Get a frame in jpeg format by reading a single image from the image folder. Goes back to first image when it reaches the last image."""
        img = self.get_cv_frame()

        return self.cv_to_jpeg(img)
        
    
    def get_cv_frame(self) -> cv2.typing.MatLike:
        """Get a frame object by reading a single image from the image folder. Goes back to first image when it reaches the last image."""

        self.index = (self.index + 1) % self.size
        img_name = self.img_names[self.index]
        img_path = os.path.join(self.img_dir, img_name)
        img = cv2.imread(img_path)
        
        return img
    
    def cv_to_jpeg(self, img : cv2.typing.MatLike) -> bytes:
        """Converts cv2 image object to jpeg"""
        jpeg = cv2.imencode(self.file_type, img)[1]
        jpeg_bytes = jpeg.tobytes()
        
        return jpeg_bytes

# class Model(hailo.Hailo_Device):
#     def __init__ (self, model_name : str = "yolov11x_mkII", folder_path : str = "models", threshold : float=0.7, shape : tuple[int, int]=(640, 640), input_type = np.float32):
#         """
#         Params:
#             model_name: hef file name
#             folder_path: path to folder keeping model .hef file
#             shape : shape of input images. Defaults to (640, 640)
#             input_type: input type of pixels. Defaults to np.float32"""
#         super().__init__(model_name, folder_path) # Load model
#         self.shape = shape
#         self.input_type = input_type
#         self.threshold = threshold

#     def infer(self, img : cv2.typing.MatLike) -> cv2.typing.MatLike:
#         """Performs inference on a single image and return a new one with the bounding boxes
        
#         Params:
#             img: image to perform inference on"""
#         _img, dw, dh, r = letterbox(img, new_shape=self.shape)
#         dataset = np.array([_img], dtype=(self.input_type))
#         result = super().infer(dataset)[0]
#         # print(result)
#         _img = draw_boxes(result, img, self.threshold, dw, dh, r, self.shape)

#         return _img
    

# if __name__ == "__main__":
#     # Do object detection on a single image for testing 
#     # folder = "data"
#     # img_names = get_img_names(folder)
#     # camera = Simulate_Camera(img_names, folder)
#     # frame = camera.get_cv_frame()
#     frame = cv2.imread("data/coyote156.jpg")
    
#     model_name = "yolov11x_mkII"
#     model_folder_path = "models"
#     model = Model(model_name=model_name, folder_path=model_folder_path)

#     frame_bbox = model.infer(frame)
#     cv2.imwrite("test.jpg", frame_bbox)
#     # save_img("test.jpg",frame_bbox)



