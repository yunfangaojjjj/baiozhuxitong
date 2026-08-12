# YOLOE自动标注系统 - 标签导出模块

import os
import cv2
import numpy as np
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from config import Config

class LabelExporter:
    def __init__(self, annotation_display, image_browser):
        """
        初始化标签导出模块
        
        Args:
            annotation_display (AnnotationDisplay): 标注显示模块实例
            image_browser (ImageBrowser): 图像浏览模块实例
        """
        self.annotation_display = annotation_display
        self.image_browser = image_browser
        self.export_dir = Config.EXPORT_CONFIG['default_export_dir']
    
    def export_single_annotation(self, image_path=None, output_dir=None):
        """
        导出单张图像的标注
        自动检测：如果标注包含分割数据则导出为 YOLO-seg 格式，否则为标准检测格式

        Args:
            image_path (str, optional): 图像路径，如果为None则使用当前图像
            output_dir (str, optional): 输出目录，如果为None则使用当前设置的导出目录

        Returns:
            bool: 导出成功返回True，否则返回False
        """
        # 获取图像路径
        if not image_path:
            image_path = self.image_browser.get_current_image_path()
            if not image_path:
                QMessageBox.warning(self.image_browser.graphics_view, "警告", "没有选中的图像！")
                return False

        # 获取输出目录
        if not output_dir:
            output_dir = self.export_dir
            if not output_dir:
                output_dir = os.path.dirname(image_path)

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 获取图像尺寸
        image = cv2.imread(image_path)
        if image is None:
            QMessageBox.warning(self.image_browser.graphics_view, "警告", f"无法读取图像: {image_path}")
            return False

        image_height, image_width = image.shape[:2]

        # 获取标注
        annotations = self.annotation_display.export_annotations()

        # 检查是否包含分割数据
        has_segmentation = any(
            ann.get('segmentation') and len(ann['segmentation']) >= 3
            for ann in annotations
        )

        # 转换为YOLO格式
        yolo_annotations = []
        for annotation in annotations:
            class_id = annotation['class_id']

            if has_segmentation and annotation.get('segmentation') and len(annotation['segmentation']) >= 3:
                # YOLO-seg 格式: class_id x1 y1 x2 y2 ... xn yn
                seg = annotation['segmentation']
                norm_points = []
                for pt in seg:
                    nx = float(pt[0]) / image_width
                    ny = float(pt[1]) / image_height
                    norm_points.append(f"{nx:.6f} {ny:.6f}")
                yolo_annotations.append(f"{class_id} " + " ".join(norm_points))
            else:
                # 标准 YOLO 检测格式: class_id x_center y_center width height
                bbox = annotation['bbox']
                x_center = (bbox[0] + bbox[2]) / 2 / image_width
                y_center = (bbox[1] + bbox[3]) / 2 / image_height
                width = (bbox[2] - bbox[0]) / image_width
                height = (bbox[3] - bbox[1]) / image_height
                yolo_annotations.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

        # 生成标签文件名
        image_name = os.path.basename(image_path)
        label_name = os.path.splitext(image_name)[0] + '.txt'
        label_path = os.path.join(output_dir, label_name)

        # 写入标签文件
        try:
            with open(label_path, 'w') as f:
                f.write('\n'.join(yolo_annotations))

            return True
        except Exception as e:
            print(f"标签文件写入失败: {e}")
            QMessageBox.warning(self.image_browser.graphics_view, "警告", f"标签文件写入失败: {e}")
            return False
    
    def export_batch_annotations(self, image_files=None, output_dir=None):
        """
        批量导出标注
        
        Args:
            image_files (list, optional): 图像文件列表，如果为None则使用当前图像列表
            output_dir (str, optional): 输出目录，如果为None则使用当前设置的导出目录
            
        Returns:
            tuple: (成功导出数量, 失败导出数量)
        """
        # 获取图像列表
        if not image_files:
            image_files = self.image_browser.image_files
            if not image_files:
                QMessageBox.warning(self.image_browser.graphics_view, "警告", "没有图像可以导出！")
                return (0, 0)
        
        # 获取输出目录
        if not output_dir:
            output_dir = self.export_dir
            if not output_dir:
                # 打开目录选择对话框
                output_dir = QFileDialog.getExistingDirectory(self.image_browser.graphics_view, "选择导出目录")
                if not output_dir:
                    return (0, 0)
                self.export_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 批量导出
        success_count = 0
        fail_count = 0
        
        for image_path in image_files:
            # 临时加载图像
            if self.image_browser.open_image(image_path):
                if self.export_single_annotation(image_path, output_dir):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1
        
        return (success_count, fail_count)
    
    def set_export_dir(self, export_dir):
        """
        设置导出目录
        
        Args:
            export_dir (str): 导出目录路径
        """
        self.export_dir = export_dir
    
    def get_export_dir(self):
        """
        获取当前导出目录
        
        Returns:
            str: 当前导出目录
        """
        return self.export_dir
    
    def validate_yolo_annotation(self, label_path, image_path):
        """
        验证YOLO标注文件（支持检测 / Pose / Seg 格式）

        Args:
            label_path (str): 标注文件路径
            image_path (str): 对应的图像路径

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # 检查图像文件是否存在
            if not os.path.exists(image_path):
                return (False, f"图像文件不存在: {image_path}")

            # 检查标注文件是否存在
            if not os.path.exists(label_path):
                return (True, "标注文件不存在")

            # 读取图像尺寸
            image = cv2.imread(image_path)
            if image is None:
                return (False, f"无法读取图像: {image_path}")

            image_height, image_width = image.shape[:2]

            # 读取标注文件
            with open(label_path, 'r') as f:
                lines = f.readlines()

            # 检查每一行
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                n_parts = len(parts)

                # 检查类别ID
                try:
                    class_id = int(parts[0])
                    if class_id < 0:
                        return (False, f"第{i+1}行类别ID无效: {class_id}")
                except ValueError:
                    return (False, f"第{i+1}行类别ID不是整数: {parts[0]}")

                # 检测格式: 5 个字段
                if n_parts == 5:
                    try:
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                    except ValueError:
                        return (False, f"第{i+1}行坐标不是浮点数: {line}")
                    if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 0 <= width <= 1 and 0 <= height <= 1):
                        return (False, f"第{i+1}行坐标超出范围: {line}")

                # Pose 格式: 5 + 3n 字段
                elif n_parts > 5 and (n_parts - 5) % 3 == 0:
                    try:
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                    except ValueError:
                        return (False, f"第{i+1}行坐标不是浮点数: {line}")
                    if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 0 <= width <= 1 and 0 <= height <= 1):
                        return (False, f"第{i+1}行坐标超出范围: {line}")
                    # 验证关键点
                    for j in range(5, n_parts, 3):
                        try:
                            kpx = float(parts[j])
                            kpy = float(parts[j+1])
                            kpv = int(parts[j+2])
                        except ValueError:
                            return (False, f"第{i+1}行关键点数据无效: {line}")
                        if not (0 <= kpx <= 1 and 0 <= kpy <= 1):
                            return (False, f"第{i+1}行关键点坐标超出范围: {line}")
                        if kpv not in (0, 1, 2):
                            return (False, f"第{i+1}行关键点可见性值无效(应为0/1/2): {kpv}")

                # Seg 格式: 1 + 2n 字段 (n >= 3)
                elif n_parts >= 7 and (n_parts - 1) % 2 == 0:
                    for j in range(1, n_parts, 2):
                        try:
                            px = float(parts[j])
                            py = float(parts[j+1])
                        except ValueError:
                            return (False, f"第{i+1}行分割坐标不是浮点数: {line}")
                        if not (0 <= px <= 1 and 0 <= py <= 1):
                            return (False, f"第{i+1}行分割坐标超出范围: {line}")

                else:
                    return (False, f"第{i+1}行格式无法识别(字段数={n_parts}): {line}")

            return (True, "标注文件有效")
        except Exception as e:
            return (False, f"验证失败: {e}")
    
    def preview_annotation(self, image_path):
        """
        预览标注结果
        
        Args:
            image_path (str): 图像路径
            
        Returns:
            list: YOLO格式的标注预览
        """
        # 临时加载图像
        if self.image_browser.open_image(image_path):
            # 获取图像尺寸
            image = cv2.imread(image_path)
            image_height, image_width = image.shape[:2]
            
            # 获取标注
            annotations = self.annotation_display.export_annotations()
            
            # 转换为YOLO格式预览
            yolo_annotations = []
            for annotation in annotations:
                bbox = annotation['bbox']
                class_id = annotation['class_id']
                class_name = annotation['class_name']
                
                # 计算归一化坐标
                x_center = (bbox[0] + bbox[2]) / 2 / image_width
                y_center = (bbox[1] + bbox[3]) / 2 / image_height
                width = (bbox[2] - bbox[0]) / image_width
                height = (bbox[3] - bbox[1]) / image_height
                
                # 添加到预览列表
                yolo_annotations.append({
                    'class_id': class_id,
                    'class_name': class_name,
                    'x_center': x_center,
                    'y_center': y_center,
                    'width': width,
                    'height': height,
                    'original_bbox': bbox
                })
            
            return yolo_annotations
        
        return []
    
    def export_annotations_with_format(self, format_type='yolo'):
        """
        导出不同格式的标注
        
        Args:
            format_type (str, optional): 导出格式，目前仅支持'yolo'
            
        Returns:
            dict: 导出结果
        """
        if format_type != 'yolo':
            return {'success': False, 'message': f"不支持的导出格式: {format_type}"}
        
        # 导出当前图像的标注
        success = self.export_single_annotation()
        
        if success:
            return {'success': True, 'message': "标注导出成功！"}
        else:
            return {'success': False, 'message': "标注导出失败！"}
    
    def get_yolo_label_path(self, image_path):
        """
        获取YOLO标签文件路径
        
        Args:
            image_path (str): 图像路径
            
        Returns:
            str: 对应的YOLO标签文件路径
        """
        image_name = os.path.basename(image_path)
        label_name = os.path.splitext(image_name)[0] + '.txt'
        return os.path.join(os.path.dirname(image_path), label_name)
    
    @staticmethod
    def parse_pose_label_file(label_path, image_width, image_height, class_list=None, lines=None):
        """
        解析 YOLO Pose 格式标注文件

        格式：class_id x_center y_center width height x1 y1 v1 x2 y2 v2 ...

        Args:
            label_path (str): 标注文件路径
            image_width (int): 图像宽度
            image_height (int): 图像高度
            class_list (list, optional): 类别名称列表
            lines (list, optional): 若传入，则解析这些行而不是读取 label_path
                （用于混合格式文件的逐行解析）

        Returns:
            list: 检测结果列表，每个元素包含 bbox, keypoints, confidence, class_id, class_name
        """
        detections = []

        if lines is None:
            if not label_path or not os.path.exists(label_path):
                return detections
            try:
                with open(label_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"读取 Pose 标注文件失败: {e}")
                return []

        try:
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                # 普通检测格式至少5个字段，Pose格式为 5 + 3*n
                if len(parts) < 5:
                    continue
                
                remaining = len(parts) - 5
                # 判断是否为 pose 格式
                if remaining > 0 and remaining % 3 != 0:
                    # 字段数不符合 pose 格式，跳过
                    continue
                
                class_id = int(parts[0])
                x_center = float(parts[1]) * image_width
                y_center = float(parts[2]) * image_height
                width = float(parts[3]) * image_width
                height = float(parts[4]) * image_height
                
                x1 = x_center - width / 2
                y1 = y_center - height / 2
                x2 = x_center + width / 2
                y2 = y_center + height / 2
                bbox = [x1, y1, x2, y2]
                
                # 解析关键点
                keypoints = []
                if remaining > 0:
                    try:
                        for i in range(5, len(parts), 3):
                            kp_x = float(parts[i]) * image_width
                            kp_y = float(parts[i+1]) * image_height
                            visibility = int(float(parts[i+2]))  # 容错：先用 float 再转 int
                            keypoints.append([kp_x, kp_y, visibility])
                    except (ValueError, IndexError):
                        # 关键点解析失败，跳过此行（可能是格式误判）
                        continue
                
                # 获取类别名称
                class_name = f'class_{class_id}'
                if class_list and len(class_list) > class_id:
                    class_name = class_list[class_id]
                
                detections.append({
                    'bbox': bbox,
                    'keypoints': keypoints,
                    'confidence': 1.0,
                    'class_id': class_id,
                    'class_name': class_name
                })
            
            return detections
        except Exception as e:
            print(f"解析 Pose 标注文件失败: {e}")
            return []

    @staticmethod
    def parse_seg_label_file(label_path, image_width, image_height, class_list=None, lines=None):
        """
        解析 YOLO-seg (分割) 格式标注文件

        格式：class_id x1 y1 x2 y2 ... xn yn
        所有坐标归一化到 [0, 1]，相对于图像宽高

        Args:
            label_path (str): 标注文件路径
            image_width (int): 图像宽度
            image_height (int): 图像高度
            class_list (list, optional): 类别名称列表
            lines (list, optional): 若传入，则解析这些行而不是读取 label_path
                （用于混合格式文件的逐行解析）

        Returns:
            list: 检测结果列表，每个元素包含 bbox, segmentation, confidence, class_id, class_name
        """
        detections = []

        if lines is None:
            if not label_path or not os.path.exists(label_path):
                return detections
            try:
                with open(label_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"读取 Seg 标注文件失败: {e}")
                return []

        try:
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                # seg 格式至少需要 class_id + 3对坐标（6个字段），共至少 7 个字段
                if len(parts) < 7:
                    continue

                # seg 格式：1 个 class_id + 偶数个坐标字段
                remaining = len(parts) - 1
                if remaining % 2 != 0:
                    # 不是偶数个坐标，跳过（可能是其他格式的行）
                    continue

                class_id = int(parts[0])

                # 解析分割多边形顶点
                segmentation = []
                for i in range(1, len(parts), 2):
                    px = float(parts[i]) * image_width
                    py = float(parts[i + 1]) * image_height
                    segmentation.append([px, py])

                # 从分割点计算边界框
                xs = [p[0] for p in segmentation]
                ys = [p[1] for p in segmentation]
                bbox = [min(xs), min(ys), max(xs), max(ys)]

                # 获取类别名称
                class_name = f'class_{class_id}'
                if class_list and len(class_list) > class_id:
                    class_name = class_list[class_id]

                detections.append({
                    'bbox': bbox,
                    'segmentation': segmentation,
                    'keypoints': [],
                    'confidence': 1.0,
                    'class_id': class_id,
                    'class_name': class_name
                })

            return detections
        except Exception as e:
            print(f"解析 Seg 标注文件失败: {e}")
            return []
