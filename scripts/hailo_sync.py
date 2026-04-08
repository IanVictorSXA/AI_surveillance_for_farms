from hailo import Hailo_Device
import scripts.img_processing_hailo8 as processing


img_folder = "data"
destination_folder = "results"
dataset, img_names = processing.get_dataset(img_folder)
dataset = dataset[:1]
img_names = img_names[:1]

myHat = Hailo_Device(model="yolov11x_mkII")
results = myHat.infer(dataset)
processing.save_results(results, img_names, img_folder, destination_folder)
