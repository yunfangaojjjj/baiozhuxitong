# YOLOE自动标注系统 - 格式转换模块
# 支持 Labelme JSON ↔ YOLO / YOLO-seg TXT 互转

import os
import json
import cv2
import numpy as np
import base64
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFileDialog, QMessageBox, QProgressDialog,
    QGroupBox, QCheckBox, QLineEdit, QTextEdit, QRadioButton,
    QListWidget, QAbstractItemView, QGridLayout, QWidget, QSpinBox,
)
from PyQt6.QtCore import Qt


class FormatConverter:
    """格式转换器 — 支持 Labelme JSON ↔ YOLO / YOLO-seg TXT"""

    # ======================================================================
    # Labelme JSON → YOLO-seg TXT
    # ======================================================================

    @staticmethod
    def labelme_json_to_yolo_txt(json_path, class_names=None, auto_build_classes=False):
        """
        单个 Labelme JSON → 单个 YOLO-seg TXT

        JSON shapes[].points 为绝对像素坐标，json 中包含 imageWidth / imageHeight。
        TXT 格式: class_id x1 y1 x2 y2 ... (归一化)

        Args:
            json_path (str): Labelme JSON 文件路径
            class_names (list, optional): 已有类别列表，用于 label→class_id 映射
            auto_build_classes (bool): 是否自动将未知 label 加入 class_names

        Returns:
            tuple: (success, message, txt_content_str, class_names_list)
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return False, f"读取 JSON 失败: {e}", "", class_names or []

        img_width = data.get('imageWidth', 0)
        img_height = data.get('imageHeight', 0)
        if img_width <= 0 or img_height <= 0:
            return False, "JSON 中缺少 imageWidth / imageHeight", "", class_names or []

        shapes = data.get('shapes', [])
        if not shapes:
            return False, "JSON 中没有标注 shapes", "", class_names or []

        if class_names is None:
            class_names = []

        txt_lines = []
        for shape in shapes:
            label = shape.get('label', 'object')
            points = shape.get('points', [])

            if len(points) < 3:
                continue  # 至少3个点才能构成多边形

            # 映射 label → class_id
            if label not in class_names:
                if auto_build_classes:
                    class_names.append(label)
                else:
                    continue  # 跳过未知类别

            class_id = class_names.index(label)

            # 归一化坐标
            norm_parts = [str(class_id)]
            for pt in points:
                nx = float(pt[0]) / img_width
                ny = float(pt[1]) / img_height
                norm_parts.append(f"{nx:.6f}")
                norm_parts.append(f"{ny:.6f}")

            txt_lines.append(" ".join(norm_parts))

        txt_content = "\n".join(txt_lines)
        if not txt_content:
            return False, "没有有效的分割标注可转换", "", class_names

        return True, f"转换成功: {len(txt_lines)} 个多边形", txt_content, class_names

    @staticmethod
    def batch_labelme_to_yolo(json_dir, output_txt_dir, class_names=None, progress_callback=None):
        """
        批量：目录下所有 Labelme JSON → YOLO-seg TXT

        Args:
            json_dir (str): JSON 文件目录
            output_txt_dir (str): TXT 输出目录
            class_names (list, optional): 已有类别列表
            progress_callback (callable, optional): 进度回调 (current, total) -> bool

        Returns:
            tuple: (success_count, fail_count, class_names)
        """
        json_files = [f for f in os.listdir(json_dir) if f.lower().endswith('.json')]
        if not json_files:
            return 0, 0, class_names or []

        if class_names is None:
            class_names = []

        os.makedirs(output_txt_dir, exist_ok=True)
        success_count = 0
        fail_count = 0

        for i, json_file in enumerate(json_files):
            if progress_callback:
                if not progress_callback(i + 1, len(json_files)):
                    break

            json_path = os.path.join(json_dir, json_file)
            base = os.path.splitext(json_file)[0]

            success, msg, txt_content, class_names = FormatConverter.labelme_json_to_yolo_txt(
                json_path, class_names, auto_build_classes=True)

            if success:
                txt_path = os.path.join(output_txt_dir, base + '.txt')
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(txt_content)
                success_count += 1
            else:
                fail_count += 1

        return success_count, fail_count, class_names

    # ======================================================================
    # YOLO-seg TXT → Labelme JSON
    # ======================================================================

    @staticmethod
    def yolo_txt_to_labelme_json(txt_path, output_json_path, image_path=None,
                                  image_width=0, image_height=0, class_names=None,
                                  include_image_data=False):
        """
        单个 YOLO-seg TXT → 单个 Labelme JSON

        TXT 格式: class_id x1 y1 x2 y2 ... (归一化)
        JSON 格式: Labelme 标准格式，含 shapes[].points (绝对坐标)

        Args:
            txt_path (str): YOLO-seg TXT 文件路径
            output_json_path (str): 输出 JSON 路径
            image_path (str, optional): 对应图像路径（用于获取尺寸 + 写入 imagePath）
            image_width (int): 图像宽度（若 image_path 不可用则手动指定）
            image_height (int): 图像高度
            class_names (list, optional): 类别名称列表，class_id → label
            include_image_data (bool): 是否在 JSON 中嵌入 base64 图像数据

        Returns:
            tuple: (success, message)
        """
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return False, f"读取 TXT 失败: {e}"

        # 获取图像尺寸
        img_filename = ""
        if image_path and os.path.exists(image_path):
            img = cv2.imread(image_path)
            if img is not None:
                image_height, image_width = img.shape[:2]
            img_filename = os.path.basename(image_path)

        if image_width <= 0 or image_height <= 0:
            return False, "无法获取图像尺寸：请提供有效的 image_path 或指定 image_width/image_height"

        # 解析 TXT 行
        shapes = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 7:  # class_id + 至少3对坐标
                continue
            # 检测格式不是 detection (恰好5字段)
            if len(parts) == 5:
                continue
            if (len(parts) - 1) % 2 != 0:
                continue

            class_id = int(parts[0])
            points = []
            for i in range(1, len(parts), 2):
                px = float(parts[i]) * image_width
                py = float(parts[i + 1]) * image_height
                points.append([px, py])

            label = f'class_{class_id}'
            if class_names and class_id < len(class_names):
                label = class_names[class_id]

            shapes.append({
                'label': label,
                'points': points,
                'group_id': None,
                'description': '',
                'shape_type': 'polygon',
                'flags': {},
                'mask': None,
            })

        if not shapes:
            return False, "TXT 中没有有效的分割标注"

        # 构建 Labelme JSON
        labelme_data = {
            'version': '5.8.3',
            'flags': {},
            'shapes': shapes,
            'imagePath': img_filename,
            'imageData': None,
            'imageHeight': image_height,
            'imageWidth': image_width,
        }

        # 可选：嵌入图像 base64
        if include_image_data and image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                img_bytes = f.read()
            labelme_data['imageData'] = base64.b64encode(img_bytes).decode('utf-8')

        try:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(labelme_data, f, ensure_ascii=False, indent=2)
            return True, f"转换成功: {len(shapes)} 个多边形 → {output_json_path}"
        except Exception as e:
            return False, f"写入 JSON 失败: {e}"

    @staticmethod
    def batch_yolo_to_labelme(txt_dir, image_dir, output_json_dir, class_names=None,
                               include_image_data=False, progress_callback=None):
        """
        批量：目录下所有 YOLO-seg TXT → Labelme JSON

        Args:
            txt_dir (str): TXT 文件目录
            image_dir (str): 对应图像目录
            output_json_dir (str): JSON 输出目录
            class_names (list, optional): 类别名称列表
            include_image_data (bool): 是否嵌入 base64 图像
            progress_callback (callable, optional): 进度回调

        Returns:
            tuple: (success_count, fail_count)
        """
        txt_files = [f for f in os.listdir(txt_dir) if f.lower().endswith('.txt')]
        if not txt_files:
            return 0, 0

        os.makedirs(output_json_dir, exist_ok=True)
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
        success_count = 0
        fail_count = 0

        for i, txt_file in enumerate(txt_files):
            if progress_callback:
                if not progress_callback(i + 1, len(txt_files)):
                    break

            txt_path = os.path.join(txt_dir, txt_file)
            base = os.path.splitext(txt_file)[0]

            # 寻找对应图像
            img_path = None
            for ext in image_extensions:
                candidate = os.path.join(image_dir, base + ext)
                if os.path.exists(candidate):
                    img_path = candidate
                    break

            json_path = os.path.join(output_json_dir, base + '.json')
            success, msg = FormatConverter.yolo_txt_to_labelme_json(
                txt_path, json_path, img_path,
                class_names=class_names,
                include_image_data=include_image_data)

            if success:
                success_count += 1
            else:
                fail_count += 1

        return success_count, fail_count

    # ======================================================================
    # 标准 YOLO 检测 TXT ↔ JSON (简化通用格式)
    # ======================================================================

    @staticmethod
    def yolo_det_txt_to_json(txt_dir, image_dir, output_json_path, class_names=None):
        """
        批量：YOLO 检测 TXT → 通用 JSON

        TXT: class_id x_center y_center width height
        JSON: [{image, image_width, image_height, annotations: [...]}]
        """
        results = []
        txt_files = [f for f in os.listdir(txt_dir) if f.lower().endswith('.txt')]
        if not txt_files:
            return False, "未找到 .txt 文件", 0

        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
        processed = 0

        for txt_file in txt_files:
            txt_path = os.path.join(txt_dir, txt_file)
            base = os.path.splitext(txt_file)[0]

            img_path = None
            img_width = img_height = 0
            for ext in image_extensions:
                candidate = os.path.join(image_dir, base + ext)
                if os.path.exists(candidate):
                    img_path = candidate
                    img = cv2.imread(img_path)
                    if img is not None:
                        img_height, img_width = img.shape[:2]
                    break

            annotations = []
            with open(txt_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) != 5:
                        continue

                    class_id = int(parts[0])
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])

                    ann = {
                        'class_id': class_id,
                        'bbox': [x_center, y_center, width, height],
                    }
                    if img_width > 0 and img_height > 0:
                        x1 = (x_center - width / 2) * img_width
                        y1 = (y_center - height / 2) * img_height
                        x2 = (x_center + width / 2) * img_width
                        y2 = (y_center + height / 2) * img_height
                        ann['bbox_abs'] = [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]
                    if class_names and class_id < len(class_names):
                        ann['class_name'] = class_names[class_id]

                    annotations.append(ann)

            results.append({
                'image': os.path.basename(img_path) if img_path else f'{base} (未找到图像)',
                'image_path': img_path or '',
                'image_width': img_width,
                'image_height': img_height,
                'annotations': annotations,
            })
            processed += 1

        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        return True, f"成功转换 {processed} 个文件", processed

    @staticmethod
    def yolo_det_json_to_txt(json_path, output_txt_dir):
        """通用检测 JSON → 批量 YOLO TXT"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            return False, "JSON 格式错误", 0

        os.makedirs(output_txt_dir, exist_ok=True)
        processed = 0

        for item in data:
            image_name = item.get('image', 'unknown')
            base = os.path.splitext(image_name)[0]
            img_width = item.get('image_width', 0)
            img_height = item.get('image_height', 0)
            annotations = item.get('annotations', [])

            txt_lines = []
            for ann in annotations:
                class_id = ann.get('class_id', 0)
                if 'bbox' in ann:
                    cx, cy, w, h = ann['bbox'][:4]
                elif 'bbox_abs' in ann and img_width > 0:
                    x1, y1, x2, y2 = ann['bbox_abs']
                    cx = (x1 + x2) / 2 / img_width
                    cy = (y1 + y2) / 2 / img_height
                    w = (x2 - x1) / img_width
                    h = (y2 - y1) / img_height
                else:
                    continue
                txt_lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

            if txt_lines:
                txt_path = os.path.join(output_txt_dir, base + '.txt')
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(txt_lines))
                processed += 1

        return True, f"成功转换 {processed} 个文件", processed

    # ======================================================================
    # 辅助
    # ======================================================================

    @staticmethod
    def load_class_names(classes_file):
        """从 classes.txt 加载类别名称列表"""
        names = []
        if os.path.exists(classes_file):
            with open(classes_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        names.append(line)
        return names

    @staticmethod
    def save_class_names(classes_file, class_names):
        """保存类别名称到 classes.txt"""
        with open(classes_file, 'w', encoding='utf-8') as f:
            for name in class_names:
                f.write(f"{name}\n")


# ==========================================================================
# 转换对话框
# ==========================================================================

class FormatConverterDialog(QDialog):
    """格式转换对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YOLO 格式转换工具 (Labelme JSON ↔ TXT)")
        self.setMinimumWidth(720)
        self.setMinimumHeight(520)
        self._build_ui()
        self._connect_signals()
        self._on_direction_changed()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ---- 转换类型 ----
        type_group = QGroupBox("转换类型")
        type_layout = QVBoxLayout(type_group)

        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("方向:"))
        self.radio_json_to_txt = QRadioButton("Labelme JSON → YOLO-seg TXT")
        self.radio_json_to_txt.setChecked(True)
        self.radio_txt_to_json = QRadioButton("YOLO-seg TXT → Labelme JSON")
        self.radio_det_txt_to_json = QRadioButton("YOLO检测 TXT → 通用JSON")
        self.radio_det_json_to_txt = QRadioButton("通用JSON → YOLO检测 TXT")
        dir_row.addWidget(self.radio_json_to_txt)
        dir_row.addWidget(self.radio_txt_to_json)
        type_layout.addLayout(dir_row)

        dir_row2 = QHBoxLayout()
        dir_row2.addWidget(self.radio_det_txt_to_json)
        dir_row2.addWidget(self.radio_det_json_to_txt)
        dir_row2.addStretch()
        type_layout.addLayout(dir_row2)

        layout.addWidget(type_group)

        # ---- 源路径 ----
        source_group = QGroupBox("源路径")
        source_layout = QGridLayout(source_group)

        self.source_label = QLabel("JSON 目录:")
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("选择 Labelme JSON 文件目录")
        self.source_browse = QPushButton("浏览...")
        source_layout.addWidget(self.source_label, 0, 0)
        source_layout.addWidget(self.source_edit, 0, 1)
        source_layout.addWidget(self.source_browse, 0, 2)
        layout.addWidget(source_group)

        # ---- 输出路径 ----
        output_group = QGroupBox("输出路径")
        out_layout = QGridLayout(output_group)

        self.output_label = QLabel("TXT 输出目录:")
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("选择 TXT 输出目录")
        self.output_browse = QPushButton("浏览...")
        out_layout.addWidget(self.output_label, 0, 0)
        out_layout.addWidget(self.output_edit, 0, 1)
        out_layout.addWidget(self.output_browse, 0, 2)
        layout.addWidget(output_group)

        # ---- 图像目录 (TXT→JSON 时需要) ----
        img_group = QGroupBox("图像目录 (TXT→JSON 时必填，用于获取尺寸)")
        img_layout = QGridLayout(img_group)

        self.image_edit = QLineEdit()
        self.image_edit.setPlaceholderText("选择对应图像所在目录")
        self.image_browse = QPushButton("浏览...")
        img_layout.addWidget(self.image_edit, 0, 0)
        img_layout.addWidget(self.image_browse, 0, 1)
        layout.addWidget(img_group)

        # ---- 类别文件 ----
        cls_group = QGroupBox("类别文件")
        cls_layout = QGridLayout(cls_group)

        self.classes_edit = QLineEdit()
        self.classes_edit.setPlaceholderText("classes.txt 路径 (可选，JSON→TXT 时会自动生成)")
        self.classes_browse = QPushButton("浏览...")
        self.auto_classes_check = QCheckBox("JSON→TXT 时自动收集类别并生成 classes.txt")
        self.auto_classes_check.setChecked(True)
        cls_layout.addWidget(self.classes_edit, 0, 0)
        cls_layout.addWidget(self.classes_browse, 0, 1)
        cls_layout.addWidget(self.auto_classes_check, 1, 0, 1, 3)
        layout.addWidget(cls_group)

        # ---- 选项 ----
        opt_group = QGroupBox("选项")
        opt_layout = QHBoxLayout(opt_group)
        self.embed_image_check = QCheckBox("在 JSON 中嵌入 base64 图像数据 (TXT→JSON)")
        self.embed_image_check.setChecked(False)
        opt_layout.addWidget(self.embed_image_check)
        opt_layout.addStretch()
        layout.addWidget(opt_group)

        # ---- 日志区域 ----
        log_group = QGroupBox("转换日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(140)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        # ---- 按钮 ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setObjectName("convert_btn")
        self.convert_btn.setMinimumHeight(38)
        self.convert_btn.setMinimumWidth(120)
        btn_layout.addWidget(self.convert_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.setMinimumHeight(38)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _connect_signals(self):
        # 方向切换
        self.radio_json_to_txt.toggled.connect(self._on_direction_changed)
        self.radio_txt_to_json.toggled.connect(self._on_direction_changed)
        self.radio_det_txt_to_json.toggled.connect(self._on_direction_changed)
        self.radio_det_json_to_txt.toggled.connect(self._on_direction_changed)

        # 浏览按钮
        self.source_browse.clicked.connect(self._browse_source)
        self.image_browse.clicked.connect(self._browse_image)
        self.classes_browse.clicked.connect(self._browse_classes)
        self.output_browse.clicked.connect(self._browse_output)

        # 操作按钮
        self.convert_btn.clicked.connect(self._convert)
        self.close_btn.clicked.connect(self.close)

    def _current_mode(self):
        """返回当前选择的转换模式"""
        if self.radio_json_to_txt.isChecked():
            return 'json_to_txt'
        elif self.radio_txt_to_json.isChecked():
            return 'txt_to_json'
        elif self.radio_det_txt_to_json.isChecked():
            return 'det_txt_to_json'
        else:
            return 'det_json_to_txt'

    def _on_direction_changed(self):
        mode = self._current_mode()
        if mode == 'json_to_txt':
            self.source_label.setText("JSON 目录:")
            self.source_edit.setPlaceholderText("Labelme JSON 文件所在目录")
            self.output_label.setText("TXT 输出目录:")
            self.output_edit.setPlaceholderText("TXT 输出目录")
            self.embed_image_check.setVisible(False)
            self.auto_classes_check.setVisible(True)
        elif mode == 'txt_to_json':
            self.source_label.setText("TXT 目录:")
            self.source_edit.setPlaceholderText("YOLO-seg TXT 文件所在目录")
            self.output_label.setText("JSON 输出目录:")
            self.output_edit.setPlaceholderText("Labelme JSON 输出目录")
            self.embed_image_check.setVisible(True)
            self.auto_classes_check.setVisible(False)
        elif mode == 'det_txt_to_json':
            self.source_label.setText("TXT 目录:")
            self.source_edit.setPlaceholderText("YOLO 检测 TXT 文件所在目录")
            self.output_label.setText("JSON 输出文件:")
            self.output_edit.setPlaceholderText("输出 .json 文件路径")
            self.embed_image_check.setVisible(False)
            self.auto_classes_check.setVisible(False)
        else:  # det_json_to_txt
            self.source_label.setText("JSON 文件:")
            self.source_edit.setPlaceholderText("通用检测 JSON 文件路径")
            self.output_label.setText("TXT 输出目录:")
            self.output_edit.setPlaceholderText("TXT 输出目录")
            self.embed_image_check.setVisible(False)
            self.auto_classes_check.setVisible(False)

    def _browse_source(self):
        mode = self._current_mode()
        if mode == 'det_json_to_txt':
            path, _ = QFileDialog.getOpenFileName(self, "选择 JSON 文件", ".", "JSON 文件 (*.json)")
        else:
            path = QFileDialog.getExistingDirectory(self, "选择源目录")
        if path:
            self.source_edit.setText(path)

    def _browse_image(self):
        path = QFileDialog.getExistingDirectory(self, "选择图像目录")
        if path:
            self.image_edit.setText(path)

    def _browse_classes(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择类别文件", ".", "Text 文件 (*.txt)")
        if path:
            self.classes_edit.setText(path)

    def _browse_output(self):
        mode = self._current_mode()
        if mode == 'det_txt_to_json':
            path, _ = QFileDialog.getSaveFileName(self, "保存 JSON 文件", "annotations.json", "JSON 文件 (*.json)")
        elif mode == 'det_json_to_txt':
            path = QFileDialog.getExistingDirectory(self, "选择 TXT 输出目录")
        elif mode == 'json_to_txt':
            path = QFileDialog.getExistingDirectory(self, "选择 TXT 输出目录")
        else:
            path = QFileDialog.getExistingDirectory(self, "选择 JSON 输出目录")
        if path:
            self.output_edit.setText(path)

    def _log(self, msg):
        self.log_text.append(msg)

    def _convert(self):
        source = self.source_edit.text().strip()
        output = self.output_edit.text().strip()
        image_dir = self.image_edit.text().strip()
        classes_file = self.classes_edit.text().strip()
        mode = self._current_mode()

        if not source:
            QMessageBox.warning(self, "警告", "请选择源路径！")
            return
        if not output:
            QMessageBox.warning(self, "警告", "请选择输出路径！")
            return
        if not os.path.exists(source):
            QMessageBox.warning(self, "警告", "源路径不存在！")
            return

        # 加载类别
        class_names = FormatConverter.load_class_names(classes_file) if classes_file else None

        self._log(f"\n{'='*50}")
        mode_names = {
            'json_to_txt': 'Labelme JSON → YOLO-seg TXT',
            'txt_to_json': 'YOLO-seg TXT → Labelme JSON',
            'det_txt_to_json': 'YOLO检测 TXT → 通用JSON',
            'det_json_to_txt': '通用JSON → YOLO检测 TXT',
        }
        self._log(f"转换类型: {mode_names.get(mode, mode)}")
        self._log(f"源: {source}")
        self._log(f"输出: {output}")

        try:
            if mode == 'json_to_txt':
                self._do_json_to_txt(source, output, class_names)
            elif mode == 'txt_to_json':
                self._do_txt_to_json(source, image_dir, output, class_names,
                                      self.embed_image_check.isChecked())
            elif mode == 'det_txt_to_json':
                success, msg, count = FormatConverter.yolo_det_txt_to_json(
                    source, image_dir, output, class_names)
                self._log(msg)
                QMessageBox.information(self, "完成", msg) if success else QMessageBox.warning(self, "失败", msg)
            else:  # det_json_to_txt
                success, msg, count = FormatConverter.yolo_det_json_to_txt(source, output)
                self._log(msg)
                QMessageBox.information(self, "完成", msg) if success else QMessageBox.warning(self, "失败", msg)
        except Exception as e:
            self._log(f"转换异常: {str(e)}")
            QMessageBox.critical(self, "错误", f"转换过程中发生异常:\n{str(e)}")

    def _do_json_to_txt(self, json_dir, output_txt_dir, class_names):
        """批量: Labelme JSON → YOLO-seg TXT"""
        auto_save_classes = self.auto_classes_check.isChecked()

        success, fail, collected = FormatConverter.batch_labelme_to_yolo(
            json_dir, output_txt_dir, class_names)

        # 自动保存 classes.txt
        if auto_save_classes and collected:
            classes_out = self.classes_edit.text().strip()
            if not classes_out:
                classes_out = os.path.join(output_txt_dir, 'classes.txt')
            else:
                classes_out = os.path.join(os.path.dirname(classes_out) or output_txt_dir,
                                           'classes.txt')
            FormatConverter.save_class_names(classes_out, collected)
            self._log(f"类别文件已保存: {classes_out}")
            self._log(f"类别列表: {collected}")

        msg = f"JSON → TXT: 成功 {success} 个, 失败 {fail} 个"
        self._log(msg)
        QMessageBox.information(self, "完成", msg)

    def _do_txt_to_json(self, txt_dir, image_dir, output_json_dir, class_names, embed_image):
        """批量: YOLO-seg TXT → Labelme JSON"""
        if not image_dir:
            QMessageBox.warning(self, "警告", "TXT→JSON 需要提供图像目录以获取尺寸！")
            return
        if not os.path.isdir(image_dir):
            QMessageBox.warning(self, "警告", "图像目录不存在！")
            return

        success, fail = FormatConverter.batch_yolo_to_labelme(
            txt_dir, image_dir, output_json_dir, class_names, embed_image)

        msg = f"TXT → JSON: 成功 {success} 个, 失败 {fail} 个"
        self._log(msg)
        QMessageBox.information(self, "完成", msg)
