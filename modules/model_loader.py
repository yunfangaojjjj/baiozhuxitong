# YOLOE自动标注系统 - 模型加载模块

from ultralytics import YOLO
import numpy as np
import cv2
from config import Config

class ModelLoader:
    def __init__(self):
        self.model = None
        self.classes = None
        self.weights_path = None
        self.confidence_threshold = Config.MODEL_CONFIG['confidence_threshold']
        self.iou_threshold = Config.MODEL_CONFIG['iou_threshold']
        self.device = Config.MODEL_CONFIG['device']
        self.supports_visual_prompt = False  # 标记模型是否支持视觉提示
        self.has_visual_vpe = False  # 标记是否有视觉提示嵌入
        self.visual_vpe = None  # 视觉提示嵌入
    
    def load_model(self, weights_path):
        """
        加载YOLOE模型
        
        Args:
            weights_path (str): 模型权重文件路径
            
        Returns:
            bool: 加载成功返回True，否则返回False
        """
        try:
            self.model = YOLO(weights_path)
            self.weights_path = weights_path
            
            # 检查模型是否支持视觉提示
            self.supports_visual_prompt = hasattr(self.model, 'set_classes')
            
            # 获取模型类别
            if hasattr(self.model, 'names'):
                # 处理不同类型的names属性
                if isinstance(self.model.names, dict):
                    # 如果是字典，直接使用
                    self.classes = self.model.names
                elif isinstance(self.model.names, list):
                    # 如果是列表，转换为字典 {index: name}
                    self.classes = {i: name for i, name in enumerate(self.model.names)}
                else:
                    # 其他情况，尝试转换为字典
                    try:
                        self.classes = dict(self.model.names)
                    except Exception:
                        # 如果转换失败，使用默认COCO类别
                        self.classes = {
                            0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane',
                            5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light',
                            10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter', 13: 'bench',
                            14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep',
                            19: 'cow', 20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe',
                            24: 'backpack', 25: 'umbrella', 26: 'handbag', 27: 'tie', 28: 'suitcase',
                            29: 'frisbee', 30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite',
                            34: 'baseball bat', 35: 'baseball glove', 36: 'skateboard', 37: 'surfboard',
                            38: 'tennis racket', 39: 'bottle', 40: 'wine glass', 41: 'cup', 42: 'fork',
                            43: 'knife', 44: 'spoon', 45: 'bowl', 46: 'banana', 47: 'apple',
                            48: 'sandwich', 49: 'orange', 50: 'broccoli', 51: 'carrot', 52: 'hot dog',
                            53: 'pizza', 54: 'donut', 55: 'cake', 56: 'chair', 57: 'couch',
                            58: 'potted plant', 59: 'bed', 60: 'dining table', 61: 'toilet',
                            62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote', 66: 'keyboard',
                            67: 'cell phone', 68: 'microwave', 69: 'oven', 70: 'toaster', 71: 'sink',
                            72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase', 76: 'scissors',
                            77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'
                        }
            else:
                # 默认COCO类别
                self.classes = {
                    0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane',
                    5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light',
                    10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter', 13: 'bench',
                    14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep',
                    19: 'cow', 20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe',
                    24: 'backpack', 25: 'umbrella', 26: 'handbag', 27: 'tie', 28: 'suitcase',
                    29: 'frisbee', 30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite',
                    34: 'baseball bat', 35: 'baseball glove', 36: 'skateboard', 37: 'surfboard',
                    38: 'tennis racket', 39: 'bottle', 40: 'wine glass', 41: 'cup', 42: 'fork',
                    43: 'knife', 44: 'spoon', 45: 'bowl', 46: 'banana', 47: 'apple',
                    48: 'sandwich', 49: 'orange', 50: 'broccoli', 51: 'carrot', 52: 'hot dog',
                    53: 'pizza', 54: 'donut', 55: 'cake', 56: 'chair', 57: 'couch',
                    58: 'potted plant', 59: 'bed', 60: 'dining table', 61: 'toilet',
                    62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote', 66: 'keyboard',
                    67: 'cell phone', 68: 'microwave', 69: 'oven', 70: 'toaster', 71: 'sink',
                    72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase', 76: 'scissors',
                    77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'
                }
            
            return True
        except Exception as e:
            print(f"模型加载失败: {e}")
            return False
    
    def set_confidence_threshold(self, threshold):
        """
        设置置信度阈值
        
        Args:
            threshold (float): 置信度阈值，范围0-1
        """
        self.confidence_threshold = max(0.0, min(1.0, threshold))
    
    def set_iou_threshold(self, threshold):
        """
        设置IoU阈值
        
        Args:
            threshold (float): IoU阈值，范围0-1
        """
        self.iou_threshold = max(0.0, min(1.0, threshold))
    
    def build_prompts(self, image, visual_prompts):
        """
        构建YOLOE模型可处理的视觉提示格式
        
        Args:
            image (numpy.ndarray): 主图像
            visual_prompts (list): 视觉提示列表
            
        Returns:
            dict: 构建好的提示字典
        """
        if not visual_prompts or image is None:
            return None
            
        h, w = image.shape[:2]
        bboxes = []
        masks = []
        cls = []
        
        for idx, prompt in enumerate(visual_prompts):
            try:
                if prompt.get("type") == "bbox":
                    xy = prompt["xyxy"]
                    # 确保xyxy是数值列表
                    if all(isinstance(coord, (int, float)) for coord in xy):
                        bboxes.append(xy)
                        cls.append(idx)
                    else:
                        print(f"警告: 边界框坐标包含非数值类型: {xy}")
                elif prompt.get("type") == "mask":
                    pts = prompt["pts"]
                    # 确保pts是数值列表
                    if all(isinstance(pt, (list, tuple)) and all(isinstance(coord, (int, float)) for coord in pt) for pt in pts):
                        # 创建掩码
                        mask = np.zeros((h, w), dtype=np.uint8)
                        cv2.fillPoly(mask, [np.array(pts, dtype=np.int32)], 1)
                        masks.append(mask[None, None])
                        cls.append(idx)
                    else:
                        print(f"警告: 掩码点包含非数值类型: {pts}")
            except Exception as e:
                print(f"处理提示 {idx} 时出错: {e}")
        
        out = {}
        if bboxes:
            try:
                out["bboxes"] = np.vstack(bboxes).astype(np.float32)
            except Exception as e:
                print(f"合并边界框时出错: {e}")
        if masks:
            try:
                out["masks"] = np.vstack(masks).astype(np.uint8)
            except Exception as e:
                print(f"合并掩码时出错: {e}")
        if cls:
            try:
                out["cls"] = np.array(cls, dtype=np.int64)
            except Exception as e:
                print(f"创建类别数组时出错: {e}")
        
        return out if out else None
    
    def predict(self, image_path, visual_prompts=None, visual_labels=None, has_new_prompt=False, use_visual_prompt_mode=False):
        """
        使用YOLOE模型进行预测，支持视觉提示
        
        Args:
            image_path (str): 图像文件路径
            visual_prompts (list): 视觉提示列表
            visual_labels (list): 视觉提示对应的标签
            has_new_prompt (bool): 是否有新的视觉提示
            use_visual_prompt_mode (bool): 是否强制使用视觉提示模式（用于同类批量标注）
            
        Returns:
            list: 检测结果列表，每个元素包含bbox, confidence, class_id, class_name
        """
        if not self.model:
            return []
        
        try:
            # 加载主图像
            image = cv2.imread(image_path)
            if image is None:
                return []
            
            # 模型预测参数
            predict_kwargs = {
                'source': image,
                'conf': self.confidence_threshold,
                'iou': self.iou_threshold,
                'device': self.device,
                'verbose': False
            }
            
            # 确定是否使用视觉提示模式
            should_use_vp = False
            is_visual_prompt_request = bool(visual_prompts)
            
            # 只有在明确请求视觉提示且模型支持时才使用视觉提示模式
            if is_visual_prompt_request and self.supports_visual_prompt:
                should_use_vp = True
            
            # 同类批量标注模式
            if use_visual_prompt_mode:
                should_use_vp = True

            if should_use_vp:
                try:
                    from ultralytics.models.yolo.yoloe.predict_vp import YOLOEVPSegPredictor

                    # 视觉提示预测会临时把类别映射改写为提示标签，
                    # 结束后必须恢复，否则后续普通预测会拿到错误的类别名
                    orig_classes = self.classes
                    try:
                        # 正常视觉提示模式
                        if is_visual_prompt_request:
                            prompts = self.build_prompts(image, visual_prompts)
                            if not prompts:
                                should_use_vp = False
                            else:
                                # 计算VPE（如果有新提示）
                                if has_new_prompt:
                                    temp_predict_kwargs = predict_kwargs.copy()
                                    temp_predict_kwargs['predictor'] = YOLOEVPSegPredictor
                                    temp_predict_kwargs['prompts'] = prompts
                                    temp_predict_kwargs['return_vpe'] = True

                                    temp_results = self.model.predict(**temp_predict_kwargs)
                                    if hasattr(self.model, 'predictor') and hasattr(self.model.predictor, 'vpe'):
                                        new_vpe = self.model.predictor.vpe
                                        if new_vpe is not None:
                                            self.visual_vpe = new_vpe
                                            self.has_visual_vpe = True

                                # 设置自定义类别
                                if visual_labels:
                                    self.classes = {i: label for i, label in enumerate(visual_labels)}
                                    if self.has_visual_vpe and self.visual_vpe is not None:
                                        self.model.set_classes(visual_labels, self.visual_vpe)

                                # 使用视觉提示专用的predictor进行预测
                                predict_kwargs['predictor'] = YOLOEVPSegPredictor
                                predict_kwargs['prompts'] = prompts
                        else:
                            # 批量标注模式（use_visual_prompt_mode=True）
                            # 确保使用视觉提示专用的predictor
                            predict_kwargs['predictor'] = YOLOEVPSegPredictor

                        # 执行预测
                        results = self.model.predict(**predict_kwargs)
                    finally:
                        self.classes = orig_classes

                except Exception as e:
                    print(f"视觉提示处理错误: {e}")
                    # 不自动重置VPE状态（按照用户要求）
                    # 直接返回空结果，避免继续出错
                    return []
            else:
                # 普通预测模式：完全不使用视觉提示相关功能
                # 使用最基本的参数，确保不涉及VPE
                basic_kwargs = {
                    'source': image,
                    'device': self.device,
                    'verbose': False
                }
                
                # 直接使用模型进行预测，不涉及任何VPE相关操作
                results = self.model.predict(**basic_kwargs)
            
            # 解析结果
            detections = []
            h, w = image.shape[:2]

            for result in results:
                boxes = result.boxes
                masks = result.masks if hasattr(result, 'masks') else None
                keypoints_data = result.keypoints if hasattr(result, 'keypoints') else None

                for i, box in enumerate(boxes):
                    bbox = box.xyxy[0].cpu().numpy().astype(int)
                    confidence = box.conf[0].cpu().numpy().item()
                    class_id = int(box.cls[0].cpu().numpy().item())
                    class_name = self.classes.get(class_id, f'class_{class_id}')

                    # 提取分割多边形 (YOLO-seg 模型)
                    segmentation = self._extract_segmentation(masks, i, w, h)

                    # 提取关键点 (YOLO-pose 模型)
                    keypoints = self._extract_keypoints(keypoints_data, i)

                    detections.append({
                        'bbox': bbox,
                        'confidence': confidence,
                        'class_id': class_id,
                        'class_name': class_name,
                        'segmentation': segmentation,
                        'keypoints': keypoints
                    })

            return detections
        except Exception as e:
            print(f"模型预测失败: {e}")
            # 不自动重置VPE状态（按照用户要求）
            return []
    
    def _extract_segmentation(self, masks, index, img_w, img_h):
        """
        从 YOLO 预测结果中提取分割多边形

        支持多种提取路径（按优先级）：
        1. masks.xy[i] — 像素坐标多边形（最常用）
        2. masks.xyn[i] — 归一化坐标多边形
        3. masks.data[i] + OpenCV 轮廓提取 — 从原始掩码位图提取（兜底）
        """
        if masks is None:
            return []

        # === 路径 1: masks.xy ===
        if hasattr(masks, 'xy') and masks.xy is not None:
            xy_val = masks.xy
            try:
                if isinstance(xy_val, list) and index < len(xy_val):
                    coords = xy_val[index]
                    if coords is not None and hasattr(coords, '__len__') and len(coords) >= 3:
                        # max_val <= 1.0 视为归一化坐标，转像素；否则视为像素坐标
                        if float(coords.max()) <= 1.0:
                            return [[float(p[0]) * img_w, float(p[1]) * img_h]
                                    for p in coords]
                        return [[float(p[0]), float(p[1])] for p in coords]
            except Exception:
                pass

        # === 路径 2: masks.xyn ===
        if hasattr(masks, 'xyn') and masks.xyn is not None:
            xyn_val = masks.xyn
            try:
                if isinstance(xyn_val, list) and index < len(xyn_val):
                    coords = xyn_val[index]
                    if coords is not None and hasattr(coords, '__len__') and len(coords) >= 3:
                        return [[float(p[0]) * img_w, float(p[1]) * img_h]
                                for p in coords]
            except Exception:
                pass

        # === 路径 3: masks.data + OpenCV 轮廓提取 ===
        if hasattr(masks, 'data') and masks.data is not None:
            data_val = masks.data
            try:
                if index < len(data_val):
                    mask_np = data_val[index].cpu().numpy()
                    if mask_np.ndim > 2:
                        mask_np = mask_np.squeeze()
                    if mask_np.ndim != 2:
                        return []

                    mask_bin = (mask_np > 0.5).astype(np.uint8)
                    if mask_bin.sum() == 0:
                        return []

                    if mask_bin.shape != (img_h, img_w):
                        mask_bin = cv2.resize(
                            mask_bin, (img_w, img_h),
                            interpolation=cv2.INTER_NEAREST
                        )

                    contours, _ = cv2.findContours(
                        mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                    )
                    if contours:
                        largest = max(contours, key=cv2.contourArea)
                        points = largest.squeeze(axis=1)
                        if points.ndim == 1:
                            points = points.reshape(-1, 2)
                        if len(points) >= 3:
                            return [[float(p[0]), float(p[1])] for p in points]
            except Exception:
                pass

        return []

    def _extract_keypoints(self, keypoints_data, index):
        """
        从 YOLO 预测结果中提取关键点 (YOLO-pose 模型)

        Args:
            keypoints_data: Ultralytics Keypoints 对象，可能为 None
            index (int): 检测结果的索引

        Returns:
            list: 关键点列表 [[x, y, visibility], ...]
        """
        if keypoints_data is None:
            return []

        if not (hasattr(keypoints_data, 'xy') and keypoints_data.xy is not None):
            return []

        try:
            kp_xy = keypoints_data.xy
            if isinstance(kp_xy, list) and index < len(kp_xy):
                kp_coords = kp_xy[index]
                if kp_coords is None or len(kp_coords) == 0:
                    return []

                keypoints = []
                if hasattr(keypoints_data, 'conf') and keypoints_data.conf is not None:
                    kp_conf = keypoints_data.conf[index]
                    for j, coord in enumerate(kp_coords):
                        vis = int(kp_conf[j]) if j < len(kp_conf) else 2
                        keypoints.append([float(coord[0]), float(coord[1]), vis])
                else:
                    for coord in kp_coords:
                        keypoints.append([float(coord[0]), float(coord[1]), 2])
                return keypoints
        except (IndexError, AttributeError, TypeError) as e:
            print(f"[关键点提取] 失败 (index={index}): {e}")

        return []

    def get_classes(self):
        """
        获取模型类别列表
        
        Returns:
            dict: 类别字典，格式为 {class_id: class_name}
        """
        return self.classes
    
    def is_model_loaded(self):
        """
        检查模型是否已加载
        
        Returns:
            bool: 模型已加载返回True，否则返回False
        """
        return self.model is not None
    
    def get_model_info(self):
        """
        获取模型信息
        
        Returns:
            dict: 模型信息字典
        """
        if not self.model:
            return {}
        
        return {
            'weights_path': self.weights_path,
            'classes_count': len(self.classes) if self.classes else 0,
            'confidence_threshold': self.confidence_threshold,
            'iou_threshold': self.iou_threshold,
            'device': self.device
        }
