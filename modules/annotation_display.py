# YOLOE自动标注系统 - 标注显示模块

import random

from PyQt6.QtWidgets import (
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsPolygonItem,
)
from PyQt6.QtGui import QBrush, QPen, QColor, QFont, QPolygonF
from PyQt6.QtCore import Qt, QRectF, QPointF

from config import Config

class AnnotationDisplay:
    def __init__(self, scene):
        """
        初始化标注显示模块
        
        Args:
            scene (QGraphicsScene): 用于显示标注的QGraphicsScene
        """
        self.scene = scene
        self.annotations = []  # 存储所有标注项
        self.selected_annotation = None  # 当前选中的标注
        self.show_annotations = True  # 是否显示标注
        
        # 标注样式配置
        self.box_thickness = Config.ANNOTATION_CONFIG['box_thickness']
        self.text_size = Config.ANNOTATION_CONFIG['text_size']
        self.default_box_color = Config.ANNOTATION_CONFIG['box_color']
        self.selected_box_color = Config.ANNOTATION_CONFIG['selected_box_color']
        self.text_color = Config.ANNOTATION_CONFIG['text_color']
        self.text_bg_color = Config.ANNOTATION_CONFIG['text_bg_color']
        
        # 关键点与骨架配置
        self.keypoint_radius = Config.ANNOTATION_CONFIG['keypoint_radius']
        self.keypoint_thickness = Config.ANNOTATION_CONFIG['keypoint_thickness']
        self.skeleton_thickness = Config.ANNOTATION_CONFIG['skeleton_thickness']
        self.keypoint_visible_color = Config.ANNOTATION_CONFIG['keypoint_visible_color']
        self.keypoint_occluded_color = Config.ANNOTATION_CONFIG['keypoint_occluded_color']
        self.keypoint_invisible_color = Config.ANNOTATION_CONFIG['keypoint_invisible_color']
        self.skeleton_color = Config.ANNOTATION_CONFIG['skeleton_color']
        self.show_keypoint_labels = Config.ANNOTATION_CONFIG['show_keypoint_labels']
        self.keypoint_names = Config.POSE_CONFIG['keypoint_names']
        self.skeleton_connections = Config.POSE_CONFIG['skeleton_connections']
        self.class_skeleton_rules = Config.POSE_CONFIG.get('class_skeleton_rules', {})

        # 分割标注配置
        self.seg_line_color = Config.ANNOTATION_CONFIG.get('seg_line_color', (0, 255, 0))
        self.seg_fill_alpha = Config.ANNOTATION_CONFIG.get('seg_fill_alpha', 80)
        self.seg_line_thickness = Config.ANNOTATION_CONFIG.get('seg_line_thickness', 2)

        # 类别颜色映射
        self.class_colors = {}
        
        # 缩放因子
        self.zoom_factor = 1.0
    
    def add_annotation(self, bbox, class_name, class_id=0, confidence=0.0, keypoints=None, segmentation=None):
        """
        添加新的标注

        Args:
            bbox (list): 边界框坐标 [x1, y1, x2, y2]
            class_name (str): 类别名称
            class_id (int, optional): 类别ID
            confidence (float, optional): 置信度
            keypoints (list, optional): 关键点列表，每个元素为 [x, y, visibility]
            segmentation (list, optional): 分割多边形顶点列表，每个元素为 [x, y]（像素坐标）

        Returns:
            dict: 标注项字典
        """
        # 如果提供了 segmentation 但未提供 bbox，从分割点计算边界框
        if segmentation is not None and bbox is None:
            xs = [p[0] for p in segmentation]
            ys = [p[1] for p in segmentation]
            bbox = [min(xs), min(ys), max(xs), max(ys)]

        # 创建标注项
        annotation = {
            'bbox': bbox,
            'class_name': class_name,
            'class_id': class_id,
            'confidence': confidence,
            'keypoints': keypoints if keypoints is not None else [],
            'segmentation': segmentation if segmentation is not None else [],
            'rect_item': None,
            'text_item': None,
            'polygon_item': None,
            'keypoint_items': [],
            'skeleton_items': [],
            'keypoint_label_items': [],
            'is_selected': False
        }
        
        # 添加到标注列表
        self.annotations.append(annotation)
        
        # 如果显示标注，则创建图形项
        if self.show_annotations:
            self._create_graphic_items(annotation)
        
        return annotation
    
    def _create_graphic_items(self, annotation):
        """
        为标注项创建图形项

        Args:
            annotation (dict): 标注项字典
        """
        x1, y1, x2, y2 = annotation['bbox']

        # 获取类别颜色
        box_color = self._get_class_color(annotation['class_id'])
        has_segmentation = annotation.get('segmentation') and len(annotation['segmentation']) >= 3

        if has_segmentation:
            # 有分割数据时：绘制多边形 + 轻量边界框
            self._create_polygon_item(annotation, box_color)

            # 绘制轻量边界框（虚线、较细）
            rect_item = QGraphicsRectItem(QRectF(x1, y1, x2 - x1, y2 - y1))
            pen = QPen(QColor(*box_color), max(1, self.box_thickness - 1), Qt.PenStyle.DashLine)
            rect_item.setPen(pen)
            rect_item.setBrush(QBrush())  # 无填充（填充由多边形提供）
            rect_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            rect_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
            rect_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
            rect_item.setZValue(5)
            rect_item.annotation = annotation
            annotation['rect_item'] = rect_item
            self.scene.addItem(rect_item)
        else:
            # 无分割数据时：使用原有矩形框样式
            rect_item = QGraphicsRectItem(QRectF(x1, y1, x2 - x1, y2 - y1))
            pen = QPen(QColor(*box_color), self.box_thickness)
            rect_item.setPen(pen)
            # 设置半透明填充，使用与边框相同的颜色
            rect_item.setBrush(QBrush(QColor(box_color[0], box_color[1], box_color[2], 50)))
            rect_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            rect_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
            rect_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
            rect_item.annotation = annotation
            annotation['rect_item'] = rect_item
            self.scene.addItem(rect_item)

        # 创建文本项（类别和置信度）
        text = f"{annotation['class_name']} ({annotation['confidence']:.2f})"
        text_item = QGraphicsTextItem(text)

        # 设置文本样式
        font = QFont()
        font.setPointSizeF(12 * self.text_size)
        font.setBold(True)
        text_item.setFont(font)
        text_item.setDefaultTextColor(QColor(*self.text_color))

        # 设置文本背景（使用半透明黑色背景）
        text_item.setOpacity(1.0)
        text_item.setZValue(10)

        # 设置文本位置（显示在框内左上角）
        text_rect = text_item.boundingRect()
        text_item.setPos(x1 + 5, y1 + 5)

        # 存储图形项引用
        annotation['text_item'] = text_item

        # 添加到场景
        self.scene.addItem(text_item)

        # 添加关键点与骨架图形项
        self._create_keypoint_items(annotation)

    def _create_polygon_item(self, annotation, box_color):
        """
        为分割标注创建多边形图形项

        Args:
            annotation (dict): 标注项字典
            box_color (tuple): RGB 颜色值
        """
        segmentation = annotation.get('segmentation', [])
        if len(segmentation) < 3:
            return

        # 构建 QPolygonF
        polygon = QPolygonF()
        for pt in segmentation:
            polygon.append(QPointF(float(pt[0]), float(pt[1])))

        # 创建多边形项
        polygon_item = QGraphicsPolygonItem(polygon)

        # 边框颜色
        pen = QPen(QColor(*box_color), self.seg_line_thickness)
        polygon_item.setPen(pen)

        # 半透明填充
        fill_color = QColor(box_color[0], box_color[1], box_color[2], self.seg_fill_alpha)
        polygon_item.setBrush(QBrush(fill_color))

        polygon_item.setZValue(3)  # 在多边形下方显示
        polygon_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        polygon_item.annotation = annotation
        annotation['polygon_item'] = polygon_item
        self.scene.addItem(polygon_item)
    
    def _create_keypoint_items(self, annotation):
        """
        为标注项创建关键点与骨架图形项
        
        Args:
            annotation (dict): 标注项字典
        """
        keypoints = annotation.get('keypoints', [])
        if not keypoints:
            return
        
        # 清理旧的关键点图形项
        self._remove_keypoint_items(annotation)
        
        radius = self.keypoint_radius
        thickness = self.keypoint_thickness
        
        # 创建关键点圆点
        for idx, kp in enumerate(keypoints):
            if len(kp) < 3:
                continue
            x, y, visibility = float(kp[0]), float(kp[1]), int(kp[2])
            
            # 根据可见性选择颜色
            if visibility == 2:
                color = self.keypoint_visible_color
            elif visibility == 1:
                color = self.keypoint_occluded_color
            else:
                color = self.keypoint_invisible_color
            
            # 创建椭圆表示关键点
            ellipse = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
            pen = QPen(QColor(*color), thickness)
            brush = QBrush(QColor(color[0], color[1], color[2], 180))
            ellipse.setPen(pen)
            ellipse.setBrush(brush)
            ellipse.setZValue(20)
            ellipse.setVisible(visibility > 0)  # 不可见的关键点默认隐藏
            annotation['keypoint_items'].append(ellipse)
            self.scene.addItem(ellipse)
            
            # 创建关键点名称标签
            if self.show_keypoint_labels and idx < len(self.keypoint_names):
                label_text = self.keypoint_names[idx]
                label_item = QGraphicsTextItem(label_text)
                font = QFont()
                font.setPointSizeF(8 * self.text_size * self.zoom_factor)
                font.setBold(True)
                label_item.setFont(font)
                label_item.setDefaultTextColor(QColor(*color))
                label_item.setPos(x + radius + 2, y - radius - 2)
                label_item.setZValue(21)
                label_item.setVisible(visibility > 0)
                annotation['keypoint_label_items'].append(label_item)
                self.scene.addItem(label_item)
        
        # 创建骨架连线
        pen = QPen(QColor(*self.skeleton_color), self.skeleton_thickness)
        self._create_skeleton_lines(annotation, keypoints, pen)
    
    def _create_skeleton_lines(self, annotation, keypoints, pen):
        """
        根据类别规则创建骨架连线
        
        Args:
            annotation (dict): 标注项字典
            keypoints (list): 关键点列表
            pen (QPen): 连线画笔
        """
        class_id = annotation.get('class_id', 0)
        class_rule = self.class_skeleton_rules.get(class_id)
        
        if class_rule and 'star_connections' in class_rule:
            # 放射状连接：中心点连接其它所有可见点
            center_idx = class_rule['star_connections']
            if center_idx < len(keypoints) and len(keypoints[center_idx]) >= 3:
                center_kp = keypoints[center_idx]
                if int(center_kp[2]) > 0:  # 中心点可见才连线
                    for idx, kp in enumerate(keypoints):
                        if idx == center_idx:
                            continue
                        if len(kp) < 3:
                            continue
                        if int(kp[2]) == 0:
                            continue
                        line = QGraphicsLineItem(center_kp[0], center_kp[1], kp[0], kp[1])
                        line.setPen(pen)
                        line.setZValue(15)
                        annotation['skeleton_items'].append(line)
                        self.scene.addItem(line)
        else:
            # 默认 COCO 骨架连接
            for connection in self.skeleton_connections:
                idx1, idx2 = connection
                if idx1 >= len(keypoints) or idx2 >= len(keypoints):
                    continue
                kp1 = keypoints[idx1]
                kp2 = keypoints[idx2]
                if len(kp1) < 3 or len(kp2) < 3:
                    continue
                # 只有两点都可见时才绘制连线
                if int(kp1[2]) == 0 or int(kp2[2]) == 0:
                    continue
                line = QGraphicsLineItem(kp1[0], kp1[1], kp2[0], kp2[1])
                line.setPen(pen)
                line.setZValue(15)
                annotation['skeleton_items'].append(line)
                self.scene.addItem(line)
    
    def _remove_keypoint_items(self, annotation):
        """
        移除标注项的关键点与骨架图形项
        
        Args:
            annotation (dict): 标注项字典
        """
        for item in annotation.get('keypoint_items', []):
            try:
                self.scene.removeItem(item)
            except RuntimeError:
                pass
        for item in annotation.get('skeleton_items', []):
            try:
                self.scene.removeItem(item)
            except RuntimeError:
                pass
        for item in annotation.get('keypoint_label_items', []):
            try:
                self.scene.removeItem(item)
            except RuntimeError:
                pass
        
        annotation['keypoint_items'] = []
        annotation['skeleton_items'] = []
        annotation['keypoint_label_items'] = []
    
    def update_annotation(self, annotation, bbox=None, class_name=None, class_id=None, confidence=None, keypoints=None, segmentation=None):
        """
        更新标注信息

        Args:
            annotation (dict): 标注项字典
            bbox (list, optional): 新的边界框坐标
            class_name (str, optional): 新的类别名称
            class_id (int, optional): 新的类别ID
            confidence (float, optional): 新的置信度
            keypoints (list, optional): 新的关键点列表
            segmentation (list, optional): 新的分割多边形顶点列表
        """
        if bbox:
            annotation['bbox'] = bbox
            # 更新矩形项
            if annotation['rect_item']:
                x1, y1, x2, y2 = bbox
                annotation['rect_item'].setRect(QRectF(x1, y1, x2 - x1, y2 - y1))

        if segmentation is not None:
            annotation['segmentation'] = segmentation
            # 更新多边形项
            if annotation.get('polygon_item'):
                polygon = QPolygonF()
                for pt in segmentation:
                    polygon.append(QPointF(float(pt[0]), float(pt[1])))
                annotation['polygon_item'].setPolygon(polygon)

        if class_name:
            annotation['class_name'] = class_name

        if class_id is not None:
            annotation['class_id'] = class_id
            # 更新颜色
            color = self._get_class_color(class_id)
            if annotation['rect_item']:
                pen = annotation['rect_item'].pen()
                pen.setColor(QColor(*color))
                annotation['rect_item'].setPen(pen)
            if annotation.get('polygon_item'):
                pen = annotation['polygon_item'].pen()
                pen.setColor(QColor(*color))
                annotation['polygon_item'].setPen(pen)

        if confidence is not None:
            annotation['confidence'] = confidence

        # 更新关键点
        if keypoints is not None:
            annotation['keypoints'] = keypoints
            self._create_keypoint_items(annotation)

        # 更新文本项
        if annotation['text_item']:
            text = f"{annotation['class_name']} ({annotation['confidence']:.2f})"
            annotation['text_item'].setPlainText(text)

            # 确保文本样式正确
            font = annotation['text_item'].font()
            font.setPointSizeF(12 * self.text_size * self.zoom_factor)
            font.setBold(True)
            annotation['text_item'].setFont(font)
            annotation['text_item'].setDefaultTextColor(QColor(*self.text_color))
            annotation['text_item'].setOpacity(1.0)
            annotation['text_item'].setZValue(10)

            # 重新定位文本（显示在框内左上角）
            x1, y1 = annotation['bbox'][:2]
            text_rect = annotation['text_item'].boundingRect()
            annotation['text_item'].setPos(x1 + 5, y1 + 5)
    
    def remove_annotation(self, annotation):
        """
        删除标注

        Args:
            annotation (dict): 标注项字典
        """
        # 避免直接比较annotation对象，因为bbox可能是numpy数组
        # 使用id()来比较对象是否为同一个
        annotation_index = None
        for i, ann in enumerate(self.annotations):
            if id(ann) == id(annotation):
                annotation_index = i
                break

        if annotation_index is not None:
            # 移除图形项，使用try-except处理已删除的对象
            try:
                if annotation['rect_item']:
                    self.scene.removeItem(annotation['rect_item'])
            except RuntimeError:
                pass

            try:
                if annotation['text_item']:
                    self.scene.removeItem(annotation['text_item'])
            except RuntimeError:
                pass

            # 移除多边形图形项
            try:
                if annotation.get('polygon_item'):
                    self.scene.removeItem(annotation['polygon_item'])
            except RuntimeError:
                pass

            # 移除关键点与骨架图形项
            self._remove_keypoint_items(annotation)

            # 从列表中移除
            del self.annotations[annotation_index]

            # 如果是选中状态，取消选中
            if id(self.selected_annotation) == id(annotation):
                self.selected_annotation = None
    
    def clear_annotations(self):
        """
        清除所有标注
        """
        for annotation in self.annotations[:]:
            self.remove_annotation(annotation)
        self.annotations = []
        self.selected_annotation = None
    
    def toggle_annotations(self):
        """
        切换标注显示状态
        """
        self.show_annotations = not self.show_annotations

        if self.show_annotations:
            # 显示所有标注
            for annotation in self.annotations:
                if not annotation['rect_item']:
                    self._create_graphic_items(annotation)
        else:
            # 隐藏所有标注
            for annotation in self.annotations:
                if annotation['rect_item']:
                    self.scene.removeItem(annotation['rect_item'])
                    annotation['rect_item'] = None
                if annotation['text_item']:
                    self.scene.removeItem(annotation['text_item'])
                    annotation['text_item'] = None
                if annotation.get('polygon_item'):
                    self.scene.removeItem(annotation['polygon_item'])
                    annotation['polygon_item'] = None
                # 隐藏关键点与骨架
                self._remove_keypoint_items(annotation)
    
    def select_annotation(self, annotation):
        """
        选择标注
        
        Args:
            annotation (dict): 要选中的标注项
        """
        # 取消之前的选中状态
        if self.selected_annotation:
            self._update_selection_state(self.selected_annotation, False)
        
        # 更新当前选中状态
        self.selected_annotation = annotation
        if annotation:
            self._update_selection_state(annotation, True)
    
    def _update_selection_state(self, annotation, is_selected):
        """
        更新标注的选中状态

        Args:
            annotation (dict): 标注项
            is_selected (bool): 是否选中
        """
        annotation['is_selected'] = is_selected

        if annotation['rect_item']:
            pen = annotation['rect_item'].pen()
            if is_selected:
                # 选中状态样式
                pen.setColor(QColor(*self.selected_box_color))
                pen.setWidth(self.box_thickness * 2)
            else:
                # 未选中状态样式
                color = self._get_class_color(annotation['class_id'])
                pen.setColor(QColor(*color))
                has_seg = annotation.get('segmentation') and len(annotation['segmentation']) >= 3
                if has_seg:
                    pen.setWidth(max(1, self.box_thickness - 1))
                else:
                    pen.setWidth(self.box_thickness)

            annotation['rect_item'].setPen(pen)

        # 更新多边形选中状态
        if annotation.get('polygon_item'):
            poly_pen = annotation['polygon_item'].pen()
            if is_selected:
                poly_pen.setColor(QColor(*self.selected_box_color))
                poly_pen.setWidth(self.seg_line_thickness + 1)
            else:
                color = self._get_class_color(annotation['class_id'])
                poly_pen.setColor(QColor(*color))
                poly_pen.setWidth(self.seg_line_thickness)
            annotation['polygon_item'].setPen(poly_pen)
    
    def get_annotation_at_point(self, point):
        """
        获取指定点的标注

        Args:
            point (QPointF): 场景中的点

        Returns:
            dict: 标注项字典，如果没有则返回None
        """
        # 优先检查多边形（分割标注在视觉上更精确）
        for annotation in self.annotations:
            try:
                if annotation.get('polygon_item') and annotation['polygon_item'].contains(point):
                    return annotation
            except RuntimeError:
                annotation['polygon_item'] = None

        # 再检查矩形框
        for annotation in self.annotations:
            try:
                if annotation['rect_item'] and annotation['rect_item'].contains(point):
                    return annotation
            except RuntimeError:
                annotation['rect_item'] = None
        return None
    
    def _get_class_color(self, class_id):
        """
        获取类别对应的颜色
        
        Args:
            class_id (int): 类别ID
            
        Returns:
            tuple: RGB颜色值
        """
        if class_id not in self.class_colors:
            # 为新类别生成随机颜色
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            self.class_colors[class_id] = (r, g, b)
        
        return self.class_colors[class_id]
    
    def set_class_colors(self, class_colors):
        """
        设置类别颜色映射

        Args:
            class_colors (dict): 类别颜色映射字典，格式为 {class_id: (r, g, b)}
        """
        self.class_colors = class_colors

        # 更新所有标注的颜色
        for annotation in self.annotations:
            color = self._get_class_color(annotation['class_id'])
            if annotation['rect_item']:
                pen = annotation['rect_item'].pen()
                pen.setColor(QColor(*color))
                annotation['rect_item'].setPen(pen)
            if annotation.get('polygon_item'):
                pen = annotation['polygon_item'].pen()
                pen.setColor(QColor(*color))
                annotation['polygon_item'].setPen(pen)
                fill_color = QColor(color[0], color[1], color[2], self.seg_fill_alpha)
                annotation['polygon_item'].setBrush(QBrush(fill_color))
    
    def get_annotations(self):
        """
        获取所有标注
        
        Returns:
            list: 标注项列表
        """
        return self.annotations
    
    def get_selected_annotation(self):
        """
        获取当前选中的标注
        
        Returns:
            dict: 当前选中的标注项，如果没有则返回None
        """
        return self.selected_annotation
    
    def update_zoom(self, zoom_factor):
        """
        更新缩放因子
        
        Args:
            zoom_factor (float): 缩放因子
        """
        self.zoom_factor = zoom_factor
        
        # 更新文本大小
        for annotation in self.annotations:
            if annotation['text_item']:
                font = annotation['text_item'].font()
                font.setPointSizeF(12 * self.text_size * zoom_factor)  # 保持与创建时一致的字体大小计算
                annotation['text_item'].setFont(font)
    
    def load_detections(self, detections):
        """
        从检测结果加载标注

        Args:
            detections (list): 检测结果列表，每个元素包含bbox, confidence, class_id, class_name, keypoints, segmentation
        """
        # 清除现有标注
        self.clear_annotations()

        # 添加新标注
        for detection in detections:
            self.add_annotation(
                bbox=detection['bbox'],
                class_name=detection['class_name'],
                class_id=detection['class_id'],
                confidence=detection['confidence'],
                keypoints=detection.get('keypoints'),
                segmentation=detection.get('segmentation')
            )
    
    def show_hide_confidence(self, show_confidence):
        """
        显示或隐藏置信度
        
        Args:
            show_confidence (bool): 是否显示置信度
        """
        for annotation in self.annotations:
            if annotation['text_item']:
                if show_confidence:
                    text = f"{annotation['class_name']} ({annotation['confidence']:.2f})"
                else:
                    text = annotation['class_name']
                annotation['text_item'].setPlainText(text)
                
                # 确保文本样式正确
                font = annotation['text_item'].font()
                font.setPointSizeF(12 * self.text_size * self.zoom_factor)  # 增加字体大小并考虑缩放
                font.setBold(True)  # 粗体显示
                annotation['text_item'].setFont(font)
                annotation['text_item'].setDefaultTextColor(QColor(*self.text_color))
                annotation['text_item'].setOpacity(1.0)  # 确保文本不透明
                annotation['text_item'].setZValue(10)  # 确保文本显示在最上层
                
                # 重新定位文本（显示在框内左上角）
                x1, y1 = annotation['bbox'][:2]
                text_rect = annotation['text_item'].boundingRect()
                annotation['text_item'].setPos(x1 + 5, y1 + 5)
    
    def export_annotations(self):
        """
        导出标注为YOLO格式

        Returns:
            list: YOLO格式的标注数据，每个元素包含class_id, bbox, class_name, keypoints, segmentation
        """
        yolo_annotations = []

        for annotation in self.annotations:
            bbox = annotation['bbox']
            class_id = annotation['class_id']

            # 计算YOLO格式的坐标（归一化）
            # 假设图像尺寸为 (width, height)，需要从外部传入
            # 这里先返回原始坐标，后续在导出模块中进行归一化
            yolo_annotations.append({
                'class_id': class_id,
                'bbox': bbox,
                'class_name': annotation['class_name'],
                'keypoints': annotation.get('keypoints', []),
                'segmentation': annotation.get('segmentation', [])
            })

        return yolo_annotations
    
    def is_annotation_selected(self):
        """
        检查是否有标注被选中
        
        Returns:
            bool: 有标注被选中返回True，否则返回False
        """
        return self.selected_annotation is not None
