# AI 标注系统 - SAM 模型加载模块（AI 多边形）
#
# 负责加载 SAM（Segment Anything Model）权重，并用点提示（前景/背景点）
# 做交互式分割，再把分割掩码转换为可标注的简化多边形。
#
# 实现说明：
# - 使用 ultralytics 底层 SAMPredictor/SAM2Predictor（set_image 缓存图像特征，
#   每次加点只跑掩码解码器，交互更跟手）；
# - 掩码从低分辨率 (256x256) 经 ops.scale_masks 还原回原图尺寸；
# - 负点提示直接传给模型（ultralytics 官网 SAM2 权重负点有效）；
#   若模型对负点无响应（如 SAM2.1/MobileSAM），自动回退为掩码 flood-fill 挖除。

import os
import shutil

import cv2
import numpy as np

from config import Config


class SAMLoader:
    """SAM 模型加载与交互式分割"""

    # 官方 SAM2/SAM2.1 权重命名 -> ultralytics 标准命名。
    # ultralytics 的 build_sam() 按文件名结尾匹配架构白名单(sam2_t.pt 等),
    # 官方文件(sam2_hiera_tiny.pt 等)不在白名单内, 但权重格式本身兼容
    # ({"model": state_dict}), 复制为标准名即可直接加载。
    SAM2_STANDARD_NAMES = {
        'sam2_hiera_tiny.pt': 'sam2_t.pt',
        'sam2_hiera_small.pt': 'sam2_s.pt',
        'sam2_hiera_base_plus.pt': 'sam2_b.pt',
        'sam2_hiera_large.pt': 'sam2_l.pt',
        'sam2.1_hiera_tiny.pt': 'sam2.1_t.pt',
        'sam2.1_hiera_small.pt': 'sam2.1_s.pt',
        'sam2.1_hiera_base_plus.pt': 'sam2.1_b.pt',
        'sam2.1_hiera_large.pt': 'sam2.1_l.pt',
    }

    # 负点有效性判定: 加负点后掩码变化小于该比例视为模型负点无效
    NEGATIVE_MIN_CHANGE_RATIO = 0.02

    def __init__(self):
        self.model = None          # ultralytics SAM 实例
        self.weights_path = None
        self.device = Config.MODEL_CONFIG['device']
        # 底层 predictor（特征缓存）
        self._predictor = None
        self._im = None            # 预处理图像 tensor
        self._orig_shape = None    # 原图 (H, W)
        self._cached_image_id = None

    # ------------------------------------------------------------------
    # 模型加载
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_standard_path(weights_path):
        """官方 SAM2 权重文件名不在 ultralytics 白名单内, 复制为标准名"""
        base = os.path.basename(weights_path)
        if base in SAMLoader.SAM2_STANDARD_NAMES:
            std_name = SAMLoader.SAM2_STANDARD_NAMES[base]
            std_path = os.path.join(os.path.dirname(weights_path), std_name)
            if not os.path.exists(std_path) or \
                    os.path.getsize(std_path) != os.path.getsize(weights_path):
                shutil.copy2(weights_path, std_path)
                print(f"[SAMLoader] 官方权重已复制为标准名: {std_path}")
            return std_path
        return weights_path

    def load_model(self, weights_path=None):
        """
        加载 SAM 权重

        Args:
            weights_path (str, optional): 权重路径，默认使用
                Config.AI_POLYGON_CONFIG['default_weights_path']

        Returns:
            tuple: (bool, str) 是否成功与提示信息
        """
        path = weights_path or Config.AI_POLYGON_CONFIG['default_weights_path']
        if not os.path.exists(path):
            return False, f"SAM 模型文件不存在: {path}"

        try:
            path = self._resolve_standard_path(path)
            from ultralytics import SAM
            self.model = SAM(path)
            self.weights_path = path
            self._predictor = None
            self._im = None
            self._cached_image_id = None
            return True, f"SAM 模型加载成功: {os.path.basename(path)}"
        except Exception as e:
            self.model = None
            self.weights_path = None
            return False, f"SAM 模型加载失败: {e}"

    def is_loaded(self):
        """模型是否已加载"""
        return self.model is not None

    # ------------------------------------------------------------------
    # 底层 predictor（图像特征缓存）
    # ------------------------------------------------------------------
    def _ensure_predictor(self):
        """按模型类型创建 SAMPredictor / SAM2Predictor"""
        if self._predictor is not None:
            return self._predictor
        from ultralytics.models.sam.predict import Predictor as SAMPredictorCls
        from ultralytics.models.sam.predict import SAM2Predictor

        predictor_cls = SAM2Predictor if self.model.is_sam2 else SAMPredictorCls
        self._predictor = predictor_cls(overrides={
            "task": "segment", "mode": "predict",
            "imgsz": [1024, 1024], "conf": 0.0,
        })
        self._predictor.setup_model(model=self.model.model, verbose=False)
        return self._predictor

    def set_image(self, image):
        """预处理图像并缓存特征（切换图像时调用）"""
        pred = self._ensure_predictor()
        pred.setup_source(image)
        assert len(pred.dataset) == 1, "set_image 仅支持单张图像"
        for batch in pred.dataset:
            im = pred.preprocess(batch[1])
            pred.features = pred.get_im_features(im)
            break
        pred.batch = [None, [image]]
        self._im = im
        self._orig_shape = image.shape[:2]
        self._cached_image_id = id(image)

    # ------------------------------------------------------------------
    # 点提示分割
    # ------------------------------------------------------------------
    def _infer(self, points, labels):
        """底层推理, 返回还原到原图尺寸的掩码 (C, H, W) 与 scores"""
        from ultralytics.utils.ops import scale_masks
        pred = self._ensure_predictor()
        masks, scores = pred.prompt_inference(
            self._im, points=[points], labels=[labels], multimask_output=False)
        H, W = self._orig_shape
        scaled = scale_masks(masks[None].float(), (H, W), padding=False)[0]
        return scaled.detach().cpu().numpy(), scores.detach().cpu().numpy()

    def predict_mask(self, image, fg_points, bg_points=None):
        """
        用点提示预测分割掩码

        负点策略: 优先传给模型(官网 SAM2 权重负点有效); 若模型对负点无响应
        (掩码几乎无变化), 自动回退为 flood-fill 挖除背景点所在连通区域,
        保证负点在任何模型下都生效。

        Args:
            image (numpy.ndarray): BGR 图像
            fg_points (list): 前景点像素坐标 [[x, y], ...]
            bg_points (list, optional): 背景点像素坐标 [[x, y], ...]

        Returns:
            numpy.ndarray or None: 二值掩码 (H, W) uint8，失败返回 None
        """
        if self.model is None or image is None:
            return None
        if not fg_points:
            return None

        try:
            # 图像变化时重新缓存特征
            if self._cached_image_id != id(image):
                self.set_image(image)

            fg = [[float(p[0]), float(p[1])] for p in fg_points]
            bg = [[float(p[0]), float(p[1])] for p in (bg_points or [])]

            if not bg:
                mask = (self._infer(fg, [1] * len(fg))[0][0] > 0.5).astype(np.uint8)
            else:
                # 1) 模型负点
                mask_bg = self._infer(fg + bg, [1] * len(fg) + [0] * len(bg))[0][0]
                # 2) 对照: 仅前景点, 判断模型负点是否有效
                mask_no_bg = self._infer(fg, [1] * len(fg))[0][0]
                mask_bg_bin = (mask_bg > 0.5).astype(np.uint8)
                mask_no_bg_bin = (mask_no_bg > 0.5).astype(np.uint8)
                diff = int((mask_bg_bin != mask_no_bg_bin).sum())
                change_ratio = diff / max(1, int(mask_no_bg_bin.sum()))
                if change_ratio < self.NEGATIVE_MIN_CHANGE_RATIO:
                    # 模型负点无效 -> 基于无负点掩码挖除背景点连通区域
                    # (注意: 不能用模型负点结果, 模型可能已把背景点像素移出掩码,
                    #  导致 remove_region_at 因背景点不在掩码内而跳过;
                    #  且必须是二值 uint8 掩码, cv2.floodFill 不支持浮点)
                    mask = mask_no_bg_bin.copy()
                    for (bx, by) in bg:
                        mask = self.remove_region_at(mask, int(bx), int(by))
                else:
                    mask = mask_bg_bin

            return (mask > 0.5).astype(np.uint8)
        except Exception as e:
            print(f"SAM 分割失败: {e}")
            return None

    # ------------------------------------------------------------------
    # 掩码转多边形
    # ------------------------------------------------------------------
    @staticmethod
    def mask_to_polygon(mask):
        """
        将二值掩码转换为简化多边形（像素坐标）

        Args:
            mask (numpy.ndarray): 二值掩码 (H, W)

        Returns:
            list: 多边形顶点 [[x, y], ...]，无效时返回 []
        """
        if mask is None:
            return []

        mask = mask.astype(np.uint8)
        if mask.sum() == 0:
            return []

        cfg = Config.AI_POLYGON_CONFIG

        # 提取外部轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []

        # 过滤小面积噪点，取最大轮廓
        contours = [c for c in contours
                    if cv2.contourArea(c) >= cfg['min_polygon_area']]
        if not contours:
            return []
        largest = max(contours, key=cv2.contourArea)

        # Douglas-Peucker 简化，控制顶点数量
        epsilon = cfg['polygon_epsilon_ratio'] * cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, epsilon, True)

        pts = approx.squeeze(axis=1)
        if pts.ndim == 1:
            pts = pts.reshape(-1, 2)
        if len(pts) < 3:
            return []

        polygon = [[float(p[0]), float(p[1])] for p in pts]

        # 顶点数上限保护：超出则均匀抽稀
        max_pts = cfg['max_polygon_points']
        if len(polygon) > max_pts:
            step = len(polygon) / max_pts
            polygon = [polygon[int(i * step) % len(polygon)]
                       for i in range(max_pts)]

        return polygon

    @staticmethod
    def remove_region_at(mask, x, y):
        """
        从二值掩码中挖除以 (x, y) 为起点的连通区域（8 连通）

        Args:
            mask (numpy.ndarray): 二值掩码 (H, W) uint8
            x (int): 背景点 x
            y (int): 背景点 y

        Returns:
            numpy.ndarray: 挖除后的掩码副本
        """
        if mask is None:
            return mask
        mask = mask.copy()
        h, w = mask.shape
        x = int(max(0, min(w - 1, x)))
        y = int(max(0, min(h - 1, y)))
        if mask[y, x] == 0:
            return mask  # 背景点不在掩码内，无需处理
        ff_mask = np.zeros((h + 2, w + 2), np.uint8)
        cv2.floodFill(mask, ff_mask, (x, y), 0, flags=8)
        return mask
