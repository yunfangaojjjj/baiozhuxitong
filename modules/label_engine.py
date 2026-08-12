# YOLOE自动标注系统 - 标注引擎模块

import os
from PyQt6.QtWidgets import QMessageBox, QApplication


class LabelEngine:
    """负责自动标注、批量标注和标注文件加载"""

    def __init__(self, mw):
        """
        Args:
            mw (MainWindow): 主窗口引用
        """
        self.mw = mw

    # ------------------------------------------------------------------
    # 自动标注
    # ------------------------------------------------------------------
    def auto_label(self):
        """对当前图像执行自动标注"""
        mw = self.mw
        if not mw.model_loader.is_model_loaded():
            QMessageBox.warning(mw, "警告", "请先加载模型！")
            return

        image_path = mw.image_browser.get_current_image_path()
        if not image_path:
            QMessageBox.warning(mw, "警告", "请先打开图像！")
            return

        detections = mw.model_loader.predict(
            image_path,
            visual_prompts=mw.visual_prompts,
            visual_labels=mw.visual_labels,
            has_new_prompt=mw.has_new_prompt,
        )
        if mw.has_new_prompt:
            mw.has_new_prompt = False

        _apply_detections(mw, detections, "自动标注")

    # ------------------------------------------------------------------
    # 同类批量标注
    # ------------------------------------------------------------------
    def similar_label_auto_label(self):
        """使用缓存的 VPE 对文件夹中所有图像批量标注"""
        mw = self.mw
        if not mw.model_loader.is_model_loaded():
            QMessageBox.warning(mw, "警告", "请先加载模型！")
            return

        current = mw.image_browser.get_current_image_path()
        if not current:
            QMessageBox.warning(mw, "警告", "请先打开图像！")
            return

        if not (hasattr(mw.model_loader, 'has_visual_vpe') and mw.model_loader.has_visual_vpe):
            QMessageBox.warning(mw, "警告", "请先创建视觉提示并成功标注至少一张图像！")
            return

        image_files = mw.image_browser.image_files
        if not image_files:
            QMessageBox.warning(mw, "警告", "当前文件夹中没有图像！")
            return

        reply = QMessageBox.question(
            mw, "同类批量标注确认",
            f"确定要对文件夹中的 {len(image_files)} 张图像进行同类批量标注吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success = 0
        for i, path in enumerate(image_files):
            if mw.image_browser._load_image(path):
                detections = mw.model_loader.predict(path, use_visual_prompt_mode=True)
                if detections:
                    mw.annotation_display.clear_annotations()
                    for d in detections:
                        mw.annotation_display.add_annotation(
                            bbox=d['bbox'], class_name=d['class_name'],
                            class_id=d['class_id'], confidence=d['confidence'],
                            segmentation=d.get('segmentation', []),
                            keypoints=d.get('keypoints', []),
                        )
                    mw.label_exporter.export_single_annotation()
                    success += 1
            mw.status_bar.showMessage(f"同类批量标注中: {i+1}/{len(image_files)}")
            QApplication.processEvents()

        # 恢复原始图像
        mw.image_browser._load_image(current)
        _load_image_annotation(mw)
        mw.update_all_panels()

        QMessageBox.information(
            mw, "同类批量标注完成",
            f"总图像数: {len(image_files)}\n成功标注: {success}",
        )
        mw.status_bar.showMessage(f"同类批量标注完成: {success}/{len(image_files)} 张")

    # ------------------------------------------------------------------
    # 普通批量标注
    # ------------------------------------------------------------------
    def batch_label(self):
        """批量标注当前文件夹（自动选择视觉提示或普通模式）"""
        mw = self.mw
        if not mw.model_loader.is_model_loaded():
            QMessageBox.warning(mw, "警告", "请先加载模型！")
            return

        current = mw.image_browser.get_current_image_path()
        if not current:
            QMessageBox.warning(mw, "警告", "请先打开一个图像！")
            return

        image_files = mw.image_browser.image_files
        if not image_files:
            QMessageBox.warning(mw, "警告", "当前文件夹中没有图像！")
            return

        has_vpe = hasattr(mw.model_loader, 'has_visual_vpe') and mw.model_loader.has_visual_vpe
        mode_text = "使用视觉提示模式" if has_vpe else "使用普通模式"

        reply = QMessageBox.question(
            mw, "批量标注确认",
            f"确定要{mode_text}对文件夹中的 {len(image_files)} 张图像进行批量标注吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success = 0
        for i, path in enumerate(image_files):
            if mw.image_browser._load_image(path):
                if has_vpe:
                    detections = mw.model_loader.predict(
                        path,
                        visual_prompts=mw.visual_prompts,
                        visual_labels=mw.visual_labels,
                        has_new_prompt=False,
                        use_visual_prompt_mode=True,
                    )
                else:
                    detections = mw.model_loader.predict(path)

                if detections:
                    mw.annotation_display.clear_annotations()
                    for d in detections:
                        mw.annotation_display.add_annotation(
                            bbox=d['bbox'], class_name=d['class_name'],
                            class_id=d['class_id'], confidence=d['confidence'],
                            segmentation=d.get('segmentation', []),
                            keypoints=d.get('keypoints', []),
                        )
                    mw.label_exporter.export_single_annotation()
                    success += 1
            mw.status_bar.showMessage(f"批量标注中: {i+1}/{len(image_files)}")
            QApplication.processEvents()

        mw.image_browser._load_image(current)
        _load_image_annotation(mw)
        mw.update_all_panels()

        QMessageBox.information(
            mw, "批量标注完成",
            f"总图像数: {len(image_files)}\n成功标注: {success}",
        )
        mw.status_bar.showMessage(f"批量标注完成: {success}/{len(image_files)} 张")

    # ------------------------------------------------------------------
    # 工具函数
    # ------------------------------------------------------------------
    @staticmethod
    def iou(bbox1, bbox2):
        """计算两个边界框的 IoU"""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        if intersection == 0:
            return 0.0
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        return intersection / (area1 + area2 - intersection)


# ------------------------------------------------------------------
# 模块级辅助函数
# ------------------------------------------------------------------

def _apply_detections(mw, detections, label):
    """将检测结果应用到标注显示并自动保存"""
    if detections:
        mw.annotation_display.clear_annotations()
        for d in detections:
            mw.annotation_display.add_annotation(
                bbox=d['bbox'], class_name=d['class_name'],
                class_id=d['class_id'], confidence=d['confidence'],
                segmentation=d.get('segmentation', []),
                keypoints=d.get('keypoints', []),
            )
        mw.status_bar.showMessage(f"{label}完成，检测到 {len(detections)} 个目标")
    else:
        mw.status_bar.showMessage(f"{label}完成，未检测到目标")
    mw.update_annotation_list()
    mw.auto_save_annotation()


def _load_image_annotation(mw):
    """
    加载当前图像对应的标注文件
    支持 YOLO 检测 / Pose / Seg 格式，且允许同一文件内混合多种格式
    （逐行判定格式，而不是把整个文件判定为单一格式）
    """
    image_path = mw.image_browser.get_current_image_path()
    if not image_path:
        return

    label_path = os.path.splitext(image_path)[0] + '.txt'
    mw.annotation_display.clear_annotations()

    if not os.path.exists(label_path):
        mw.update_annotation_list()
        return

    try:
        ih, iw = mw.image_browser.image_height, mw.image_browser.image_width
        class_list = mw.manual_editor.class_list

        with open(label_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        detections = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            n = len(parts)

            # 检测格式: class_id xc yc w h
            if n == 5:
                class_id = int(parts[0])
                xc = float(parts[1]) * iw
                yc = float(parts[2]) * ih
                w = float(parts[3]) * iw
                h = float(parts[4]) * ih
                bbox = [xc - w / 2, yc - h / 2, xc + w / 2, yc + h / 2]
                class_name = f'class_{class_id}'
                if len(class_list) > class_id:
                    class_name = class_list[class_id]
                detections.append({
                    'bbox': bbox,
                    'class_name': class_name,
                    'class_id': class_id,
                    'confidence': 1.0,
                    'keypoints': [],
                    'segmentation': [],
                })
                continue

            # Pose 格式: class_id xc yc w h + 3*n (x y v)，visibility 必须为 0/1/2
            is_pose = (n - 5) > 0 and (n - 5) % 3 == 0
            if is_pose:
                for vi in range(7, n, 3):
                    try:
                        v = float(parts[vi])
                        if v != int(v) or int(v) not in (0, 1, 2):
                            is_pose = False
                            break
                    except ValueError:
                        is_pose = False
                        break

            # Seg 格式: class_id + 2*n 个坐标（n >= 3）
            is_seg = n >= 7 and (n - 1) % 2 == 0

            if is_pose:
                detections.extend(mw.label_exporter.parse_pose_label_file(
                    None, iw, ih, class_list, lines=[line]))
            elif is_seg:
                detections.extend(mw.label_exporter.parse_seg_label_file(
                    None, iw, ih, class_list, lines=[line]))
            # 其它情况（字段数异常的行）直接忽略，保持与旧行为一致

        if detections:
            mw.annotation_display.load_detections(detections)

        mw.update_annotation_list()
    except Exception as e:
        print(f"加载标注失败: {e}")
