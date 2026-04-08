import numpy as np
from hailo_platform import VDevice
import cv2
from img_processing_hailo10 import letterbox, draw_boxes 
import os
import time
timeout_ms = 1000

# The output layer(s) to be retrieved after inference
outputs = ("conv61",
           "conv64",
           "conv77",
           "conv80",
           "conv91",
           "conv94")  

models = {"yolo26n": {"model_path": "models/yolo26n_mkIII_Radam_960_150_nms.hef", "outputs": outputs, "input_shape": (960, 960), "classes": ("coyote", "fox", "feral hog")},
          "yolo26n2": {"model_path": "models/yolo26n_mkIII_Radam_960_2.hef", "outputs": outputs, "input_shape": (960, 960), "classes": ("coyote", "fox", "feral hog")}}

class yolo_hailo:

    def __init__(self, model): # TODO save resizing parameters to avoid recomputing them every inference
        info = models[model] if model in models else None
        self.model_path = info["model_path"] if info else model
        self.outputs = info["outputs"] if info else outputs
        self.input_shape = info["input_shape"] if info else (960, 960)
        self.classes = info["classes"] if info else ("coyote", "fox", "feral hog")

        file_name = os.path.split(self.model_path)[1]
        self.model_name = os.path.splitext(file_name)[0]

        # YOLO params
        self.STRIDES = [8, 16, 32]
        ratio = self.input_shape[0] / 640
        self.GRID_SIZES = [
            int(80 * ratio),
            int(40 * ratio),
            int(20 * ratio),
        ]

        self.vdevice = VDevice()

        self.infer_model = self.vdevice.create_infer_model(self.model_path)
        self.configured_infer_model = self.infer_model.configure()

        self.bindings = self.configured_infer_model.create_bindings()

        
        # Get quantization parameters for outputs
        self.scales = {}
        self.zero_points = {}

        for output in self.outputs:
            name = self.model_name + "/" + output
            qinfo = self.infer_model.output(name).quant_infos[0]

            self.scales[output] = qinfo.qp_scale
            self.zero_points[output] = qinfo.qp_zp

        
        # set up output buffers
        self.output_buffers = {}

        for output in self.outputs:
            name = self.model_name + "/" + output
            shape = self.infer_model.output(name).shape

            buffer = np.empty(shape, dtype=np.uint8)

            self.output_buffers[output] = buffer
            self.bindings.output(name).set_buffer(buffer)

    def infer(self, img, conf_threshold=0.5):
        _img, dw, dh, r = letterbox(img, new_shape=self.input_shape)
        
        if conf_threshold < 0.05:
            conf_threshold = 0.05
        
        # update input buffer
        self.bindings.input().set_buffer(_img)

        # inference
        self.configured_infer_model.run([self.bindings], timeout_ms)

        buffers = {
            output: self.output_buffers[output]
            for output in self.outputs
        }

        # Postprocess
        outputs = self.postprocess(buffers, conf_threshold)


        # Draw
        # draw_boxes(outputs, img, conf_threshold, dw, dh, r)

        return outputs, dw, dh, r
        # return img
    
    def infer_with_time(self, img, conf_threshold=0.5):

        t0 = time.time()

        _img, dw, dh, r = letterbox(img, new_shape=self.input_shape)
        t_letterbox = time.time()

        print("Letterbox time:", t_letterbox - t0)

        # update input buffer
        self.bindings.input().set_buffer(_img)

        # inference
        self.configured_infer_model.run([self.bindings], timeout_ms)

        t1 = time.time()
        print("Inference time:", t1 - t_letterbox)

        buffers = {
            output: self.output_buffers[output]
            for output in self.outputs
        }

        # Postprocess
        t2 = time.time()
        outputs = self.postprocess(buffers, conf_threshold)
        t3 = time.time()

        print("Postprocessing time:", t3 - t2)

        # Draw
        draw_boxes(outputs, img, conf_threshold, dw, dh, r)

        t4 = time.time()
        print("Drawing time:", t4 - t3)
        print("Total time:", t4 - t0)

        return outputs, img

    def postprocess(self, tensors, conf_threshold=0.5):
        # adapted from https://github.com/DanielDubinsky/yolo26_hailo/blob/main/python/common.py
        tensors = {
            o: self.dequantize(tensors[o], self.scales[o], self.zero_points[o])
            for o in self.outputs
        }

        logit_threshold = -np.log(1.0 / conf_threshold - 1.0)

        results = []

        for scale_idx in range(len(self.STRIDES)):

            stride = self.STRIDES[scale_idx]
            grid_dim = self.GRID_SIZES[scale_idx]

            reg_data = tensors[self.outputs[scale_idx * 2]]
            cls_data = tensors[self.outputs[scale_idx * 2 + 1]]

            cls_flat = cls_data.reshape(-1, 3)
            reg_flat = reg_data.reshape(-1, 4)

            max_logits = cls_flat.max(axis=1)
            class_ids = cls_flat.argmax(axis=1)

            mask = max_logits > logit_threshold
            if not mask.any():
                continue

            indices = np.where(mask)[0]

            scores = self.sigmoid(max_logits[indices])
            cls = class_ids[indices]

            rows = indices // grid_dim
            cols = indices % grid_dim

            l = np.maximum(reg_flat[indices, 0], 0)
            t = np.maximum(reg_flat[indices, 1], 0)
            r = np.maximum(reg_flat[indices, 2], 0)
            b = np.maximum(reg_flat[indices, 3], 0)

            x1 = (cols + 0.5 - l) * stride
            y1 = (rows + 0.5 - t) * stride
            x2 = (cols + 0.5 + r) * stride
            y2 = (rows + 0.5 + b) * stride

            for j in range(len(indices)):
                results.append({
                    "x1": float(x1[j]),
                    "y1": float(y1[j]),
                    "x2": float(x2[j]),
                    "y2": float(y2[j]),
                    "conf": float(scores[j]),
                    "cls_id": int(cls[j]),
                })

        return results

    def sigmoid(self, x):
        return 1.0 / (1.0 + np.exp(-x))

    def dequantize(self, x, scale, zp):
        return (x.astype(np.float32) - zp) * scale

    def close(self):
        """Release Hailo resources."""
        self.configured_infer_model.deactivate()
        self.configured_infer_model.shutdown()
        self.vdevice.release()

if __name__ == "__main__":
    model_path = "models/yolo26n_mkIII_Radam_960_150_nms.hef"
    input_shape = (960, 960)
    model = yolo_hailo(model_path, outputs, input_shape)
    import time
    img = cv2.imread("data/coyote260.jpg")
    print(img.shape)
    outputs, img = model.infer_with_time(img, conf_threshold=0.5) 
    model.close()
    # print(outputs)
    # print(outputs)
    cv2.imshow("Detections", img)

    cv2.waitKey(0)
    cv2.destroyAllWindows()