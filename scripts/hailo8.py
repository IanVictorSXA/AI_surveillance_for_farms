# Based on HailoRT python api tutorial (sinc. version)
# https://hailo.ai/developer-zone/documentation/hailort-v4-23-0/?sp_referrer=tutorials_notebooks/notebooks/HRT_2_Infer_Pipeline_Inference_Tutorial.html
# Desc: Make a class to simplify inference

from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams,
    InputVStreamParams, OutputVStreamParams, FormatType)
import os
import numpy as np

path_models = "models/"

class Hailo_Device:

    def __init__(self, model : str, path_models : str="models/"):
        """model : name of the hef file
           path_models : path to folder that has hef file"""
        
        # The target can be used as a context manager ("with" statement) to ensure it's released on time.
        # Here it's avoided for the sake of simplicity
        self.model = model
        self.target = VDevice()
        # Loading compiled HEFs to device:
        hef_path = os.path.join(path_models, "{}.hef".format(self.model))
        hef = HEF(hef_path)
        
        # Configure network groups
        configure_params = ConfigureParams.create_from_hef(hef=hef, interface=HailoStreamInterface.PCIe)
        network_groups = self.target.configure(hef, configure_params)
        self.network_group = network_groups[0]
        self.network_group_params = self.network_group.create_params()
        # Create input and output virtual streams params
        self.input_vstreams_params = InputVStreamParams.make(self.network_group, format_type=FormatType.FLOAT32)
        self.output_vstreams_params = OutputVStreamParams.make(self.network_group, format_type=FormatType.FLOAT32)

        # Define dataset params
        self.input_vstream_info = hef.get_input_vstream_infos()[0]
        self.output_vstream_info = hef.get_output_vstream_infos()[0]
        
    def infer(self, dataset : np.ndarray):
        """
        Takes in an array of images and returns a list of coordinates for each image.
        Params:
            dataset : numpy array of pictures in the accepted format by the model
            
        Returns: 
            List of Ragged arrays.The list has an array for each image. 
            Each array has an array for each class. Each class array has an array for each detection (up to the maximum set on the nms_config.json file).
            Each detection array contains 5 values (Ymin, Xmin, Ymax, Xmax, Confidence, respectively. At least for my yolov11x)"""

        input_data = {self.input_vstream_info.name: dataset}
        # Infer
        with InferVStreams(self.network_group, self.input_vstreams_params, self.output_vstreams_params) as infer_pipeline:
            with self.network_group.activate(self.network_group_params):
                infer_results = infer_pipeline.infer(input_data)
                results = infer_results[self.output_vstream_info.name]
                # print(infer_pipeline.get_hw_time()) - How long it took to infer

        return results

if __name__ == "__main__":
    import cv2 as cv
    
    test = Hailo_Device("yolo26n_mkIII_Radam_960_150_nms")

    frame = [cv.imread("data/coyote156.jpg")]

    result = test.infer(frame)

    print(result)