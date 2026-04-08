import numpy as np
from hailo_platform import VDevice
import cv2
from img_processing_hailo10 import letterbox, draw_boxes 
# from hailo_platform import 
timeout_ms = 1000
# The vdevice is used as a context manager (”with” statement) to ensure it's released on time
model_name = "yolo26n_mkIII_Radam_960_150_nms"  # The name of the model to be used for inference
outputs = ("conv61",
           "conv64",
           "conv77",
           "conv80",
           "conv91",
           "conv94")  # The output layer(s) to be retrieved after inference

output_pairs = (())
buffers = {}  # A list to hold the output buffers for each specified output layer

def sigmoid(x):
    """Vectorized sigmoid function."""
    return 1.0 / (1.0 + np.exp(-x))

def dequantize(x, scale, zp):
    return (x.astype(np.float32) - zp) * scale

def postprocess(tensors, scales, zero_points, conf_threshold=0.5):
    """Run python head logic on dequantized Hailo outputs (vectorized)."""
    tensors = {output: dequantize(tensors[output], scales[output], zero_points[output]) for output in outputs}
    STRIDES = [8, 16, 32]
    GRID_SIZES = [120, 60, 30]
    logit_threshold = -np.log(1.0 / conf_threshold - 1.0)
    
    results = []
    # classes = DetectionPostProcessor._load_coco_classes()
    
    for scale_idx in range(len(STRIDES)):
        stride = STRIDES[scale_idx]
        grid_dim = GRID_SIZES[scale_idx]
        
        reg_data = tensors[outputs[scale_idx * 2]]  # (H, W, 4) reg
        cls_data = tensors[outputs[scale_idx * 2 + 1]]# (H, W, 3) cls
        
        # Reshape to (H*W, C)
        cls_flat = cls_data.reshape(-1, 3)
        reg_flat = reg_data.reshape(-1, 4)
        
        # Vectorized: find max logit and class per anchor
        max_logits = cls_flat.max(axis=1)       # (H*W,)
        class_ids = cls_flat.argmax(axis=1)      # (H*W,)
        
        # Filter by logit threshold
        mask = max_logits > logit_threshold
        if not mask.any():
            continue
        
        indices = np.where(mask)[0]
        scores = sigmoid(max_logits[indices])
        cls = class_ids[indices]
        
        # Grid coordinates
        rows = indices // grid_dim
        cols = indices % grid_dim
        
        # Decode boxes
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
                'x1': round(float(x1[j]), 2),
                'y1': round(float(y1[j]), 2),
                'x2': round(float(x2[j]), 2),
                'y2': round(float(y2[j]), 2),
                'conf': round(float(scores[j]), 4),
                'cls_id': int(cls[j]),
                # 'cls_name': coco_classes.get(int(cls[j]), 'N/A')
            })
    
    return results

with VDevice() as vdevice:

    # Create an infer model from an HEF:
    infer_model = vdevice.create_infer_model(f'models/{model_name}.hef')
    scales = {}
    zero_points = {}
    for output in outputs:
        scales[output] = infer_model.output(f"yolo26n_mkIII_Radam_960_150_nms/{output}").quant_infos[0].qp_scale
        zero_points[output] = infer_model.output(f"yolo26n_mkIII_Radam_960_150_nms/{output}").quant_infos[0].qp_zp
        print(f"Output: {output}, Scale: {scales[output]}, Zero Point: {zero_points[output]}")
    # Configure the infer model and create bindings for it
    with infer_model.configure() as configured_infer_model:
        bindings = configured_infer_model.create_bindings()
        # Set input and output buffers
        # buffer = np.empty(infer_model.input().shape).astype(np.uint8)
        img = cv2.imread("data/fox240.jpg")
        img_letterboxed = letterbox(img, new_shape=(960, 960))[0]
        print(img_letterboxed.shape, img_letterboxed.dtype)
        # print(buffer)
        # print(buffer.shape)
        bindings.input().set_buffer(img_letterboxed)

        # buffer = np.empty(infer_model.output().shape).astype(np.uint8)
        # bindings.output().set_buffer(buffer)
        for output in outputs:
            buffer = np.empty(infer_model.output(f"yolo26n_mkIII_Radam_960_150_nms/{output}").shape).astype(np.uint8)
            bindings.output(f"yolo26n_mkIII_Radam_960_150_nms/{output}").set_buffer(buffer)
        
        # Run synchronous inference and access the output buffers
        configured_infer_model.run([bindings], timeout_ms)
        # buffer = bindings.output().get_buffer().astype(np.float32)
        # buffer = (buffer - zero_point) * scale
        buffers = {}

        for output in outputs:
            buffer = bindings.output(f"yolo26n_mkIII_Radam_960_150_nms/{output}").get_buffer()
            buffers[output] = buffer

        # # Run asynchronous inference
        # job = configured_infer_model.run_async([bindings])
        # job.wait(timeout_ms)

# for name, buffer in buffers.items():
#     # print(buffer)
#     print(name, buffer.shape)
outputs = postprocess(buffers, scales=scales, zero_points=zero_points)
outputs_arr = [[output['x1'], output['y1'], output['x2'], output['y2'], output['conf'], output['cls_id']] for output in outputs]
print(outputs)
img_detected = draw_boxes(outputs, img_letterboxed, threshold=0.5, model_input=(960, 960))
cv2.imshow("Detections", img_detected)

cv2.waitKey(0)
cv2.destroyAllWindows()
# print(postprocess(buffer[0]).min(), postprocess(buffer[0]).max())
# postprocessed_results = postprocess(buffers)
# print(len(postprocessed_results))