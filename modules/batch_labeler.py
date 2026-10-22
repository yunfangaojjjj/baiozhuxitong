# AI 标注系统 - 批量模型标注模块（纯推理逻辑，UI 入口在主窗口右侧面板）
#
# 用训练好的 YOLO 检测 / 分割 / Pose 权重对整批图像推理，
# 自动生成同名 .txt 标签（预标注），供后续人工修正。
#
# 输出格式与 label_exporter 的解析规则一一对应：
#   detect  -> class_id xc yc w h
#   segment -> class_id x1 y1 x2 y2 ... xn yn
#   pose    -> class_id xc yc w h x1 y1 v1 x2 y2 v2 ...（17 关键点，v∈{0,2}）

import os


def _clamp01(v):
    return max(0.0, min(1.0, float(v)))


class BatchLabeler:
    """YOLO 权重加载与批量推理（模型缓存，加载一次可反复标注）"""

    def __init__(self, mw):
        self.mw = mw
        self.model = None
        self.task = 'detect'
        self.class_names = []
        self.weights_path = None

    def load_model(self, weights_path):
        """
        加载 YOLO 权重并缓存

        Args:
            weights_path (str): YOLO 权重路径

        Returns:
            tuple: (bool, str) 是否成功与提示信息
        """
        from ultralytics import YOLO
        try:
            self.model = YOLO(weights_path)
        except Exception as e:
            self.model = None
            self.weights_path = None
            return False, f"加载模型失败: {e}"

        self.weights_path = weights_path
        self.task = getattr(self.model, 'task', 'detect')
        self.class_names = self._class_names(self.model)
        return True, f"已加载: {os.path.basename(weights_path)} ({self.task}, {len(self.class_names)} 类)"

    def is_loaded(self):
        """模型是否已加载"""
        return self.model is not None

    @staticmethod
    def _class_names(model):
        """从模型提取类别名列表（按 class_id 顺序）"""
        names = getattr(model, 'names', None)
        if isinstance(names, dict):
            keys = sorted(names.keys())
            return [names.get(k, f'class_{k}') for k in keys]
        if isinstance(names, (list, tuple)):
            return list(names)
        return []

    def run(self, image_files, conf=0.25, iou=0.45, progress_callback=None):
        """
        用已加载的模型批量推理并写同名 .txt 标签

        Args:
            image_files (list): 图像路径列表
            conf (float): 置信度阈值
            iou (float): NMS IoU 阈值
            progress_callback (callable, optional): (current, total) -> bool，
                返回 False 中断

        Returns:
            tuple: (success_count, fail_count)
        """
        if self.model is None:
            return 0, 0

        total = len(image_files)
        success = 0
        fail = 0

        for i, image_path in enumerate(image_files):
            if progress_callback and not progress_callback(i + 1, total):
                break
            try:
                results = self.model.predict(
                    source=image_path, conf=conf, iou=iou, verbose=False)
                lines = self._to_yolo_lines(results[0], self.task)
                label_path = os.path.splitext(image_path)[0] + '.txt'
                with open(label_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                success += 1
            except Exception as e:
                print(f"[BatchLabeler] {os.path.basename(image_path)} 失败: {e}")
                fail += 1

        return success, fail

    @staticmethod
    def _to_yolo_lines(result, task):
        """
        将单个 ultralytics Results 转换为 YOLO 标签行

        Args:
            result: ultralytics Results 对象
            task (str): 'detect' / 'segment' / 'pose'

        Returns:
            list: 标签行字符串列表
        """
        lines = []
        boxes = getattr(result, 'boxes', None)
        if boxes is None or len(boxes) == 0:
            return lines

        cls = boxes.cls.cpu().numpy().astype(int)
        xyxyn = boxes.xyxyn.cpu().numpy()  # 归一化 xyxy

        masks = getattr(result, 'masks', None) if task == 'segment' else None
        keypoints = getattr(result, 'keypoints', None) if task == 'pose' else None

        if masks is not None:
            # segment: class_id x1 y1 ... xn yn
            for k in range(len(boxes)):
                try:
                    poly = masks.xyn[k]
                except (IndexError, AttributeError):
                    continue
                if len(poly) < 3:
                    continue
                parts = [str(int(cls[k]))]
                for p in poly:
                    parts.append(f"{_clamp01(p[0]):.6f} {_clamp01(p[1]):.6f}")
                lines.append(' '.join(parts))
        elif keypoints is not None:
            # pose: class_id xc yc w h + 17 组 (x y v)
            for k in range(len(boxes)):
                try:
                    kps = keypoints.xyn[k]
                except (IndexError, AttributeError):
                    continue
                x1, y1, x2, y2 = xyxyn[k]
                parts = [
                    str(int(cls[k])),
                    f"{(x1 + x2) / 2:.6f}", f"{(y1 + y2) / 2:.6f}",
                    f"{(x2 - x1):.6f}", f"{(y2 - y1):.6f}",
                ]
                for kp in kps:
                    # 可见性：检测到(置信度>0)为 2，否则 0（无遮挡概念）
                    v = 2 if float(kp[2]) > 0.0 else 0
                    parts.append(f"{_clamp01(kp[0]):.6f} {_clamp01(kp[1]):.6f} {v}")
                lines.append(' '.join(parts))
        else:
            # detect: class_id xc yc w h
            for k in range(len(boxes)):
                x1, y1, x2, y2 = xyxyn[k]
                lines.append(
                    f"{int(cls[k])} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} "
                    f"{(x2 - x1):.6f} {(y2 - y1):.6f}")

        return lines
