# YOLOE自动标注系统 - 主应用

import sys
import os
import shutil

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QListWidgetItem, QTreeWidgetItem, QProgressDialog,
    QGraphicsRectItem, QInputDialog,
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPen, QColor

# 导入自定义模块
from modules.model_loader import ModelLoader
from modules.image_browser import ImageBrowser, CustomGraphicsView
from modules.annotation_display import AnnotationDisplay
from modules.manual_editor import ManualEditor
from modules.label_exporter import LabelExporter
from modules.dataset_organizer import DatasetOrganizer
from modules.format_converter import FormatConverterDialog
from modules.ui_builder import UIBuilder
from modules.class_manager import ClassManager
from modules.label_engine import LabelEngine, _load_image_annotation
from config import Config


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # ---- 状态变量 ----
        self.is_middle_pressed = False
        self.last_mouse_pos = None

        # 视觉提示相关
        self.visual_drawing = False
        self.current_visual_prompt = None
        self.visual_prompts = []
        self.visual_labels = []
        self.visual_vpe = None
        self.has_new_prompt = False
        self.drawing_start = None
        self.drawing_rect = None

        # 保存相关
        self.save_folder = None

        # 模型状态
        self.model_loaded = False

        # ---- 构建 UI ----
        self.ui_builder = UIBuilder(self)
        self.ui_builder.build()

        # ---- 初始化模块 ----
        self._init_modules()

        # ---- 连接信号 ----
        self._init_connections()

    # ==================================================================
    # 模块初始化
    # ==================================================================
    def _init_modules(self):
        """初始化所有功能模块"""
        self.image_browser = ImageBrowser(self.graphics_view)
        self.annotation_display = AnnotationDisplay(self.image_browser.scene)
        self.manual_editor = ManualEditor(self.annotation_display, self.image_browser)
        self.manual_editor.main_window = self
        self.model_loader = ModelLoader()
        self.label_exporter = LabelExporter(self.annotation_display, self.image_browser)
        self.dataset_organizer = DatasetOrganizer(self.image_browser, self.annotation_display)
        self.class_manager = ClassManager(self)
        self.label_engine = LabelEngine(self)

    # ==================================================================
    # 信号连接
    # ==================================================================
    def _init_connections(self):
        self.conf_slider.valueChanged.connect(self._on_conf_change)
        self.iou_slider.valueChanged.connect(self._on_iou_change)

        if hasattr(self, 'folder_tree'):
            self.folder_tree.itemDoubleClicked.connect(self._on_tree_double_click)
            self.folder_tree.itemClicked.connect(self._on_tree_click)

        self.annotation_list.itemClicked.connect(self._on_anno_item_click)
        self.annotation_list.currentRowChanged.connect(self._on_anno_row_change)

        # 鼠标/滚轮事件覆写
        self.image_browser.scene.mousePressEvent = self._mouse_press
        self.image_browser.scene.mouseMoveEvent = self._mouse_move
        self.image_browser.scene.mouseReleaseEvent = self._mouse_release
        self.graphics_view.wheelEvent = self._wheel

    # ==================================================================
    # 事件处理
    # ==================================================================
    def _mouse_press(self, event):
        if self.visual_drawing:
            self.drawing_start = event.scenePos()
        else:
            self.manual_editor.handle_mouse_press(event)

    def _mouse_move(self, event):
        if self.visual_drawing:
            self.image_browser.update_crosshair(event.scenePos())
        if self.visual_drawing and self.drawing_start:
            if self.drawing_rect:
                self.image_browser.scene.removeItem(self.drawing_rect)
            r = QRectF(self.drawing_start, event.scenePos()).normalized()
            self.drawing_rect = QGraphicsRectItem(r)
            pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine)
            self.drawing_rect.setPen(pen)
            self.drawing_rect.setZValue(1000)
            self.image_browser.scene.addItem(self.drawing_rect)
        else:
            self.manual_editor.handle_mouse_move(event)

    def _mouse_release(self, event):
        if self.visual_drawing and self.drawing_start:
            pos = event.scenePos()
            x1 = min(self.drawing_start.x(), pos.x())
            y1 = min(self.drawing_start.y(), pos.y())
            x2 = max(self.drawing_start.x(), pos.x())
            y2 = max(self.drawing_start.y(), pos.y())
            if x2 - x1 < 5 or y2 - y1 < 5:
                QMessageBox.warning(self, "警告", "边界框太小，请重新绘制！")
            else:
                self._finish_visual_drawing([x1, y1, x2, y2])
            if self.drawing_rect:
                self.image_browser.scene.removeItem(self.drawing_rect)
                self.drawing_rect = None
            self.drawing_start = None
        else:
            self.manual_editor.handle_mouse_release(event)
            self.update_all_panels()

    def _wheel(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.image_browser.zoom_in()
        else:
            self.image_browser.zoom_out()
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_A:
            self.previous_image()
        elif key == Qt.Key.Key_D:
            self.next_image()
        elif key == Qt.Key.Key_Space:
            self.save_current_image()
            self.next_image()
        else:
            self.manual_editor.handle_key_press(event)
            super().keyPressEvent(event)

    # ==================================================================
    # 文件夹树
    # ==================================================================
    def populate_folder(self, parent_item, folder_path):
        parent_item.takeChildren()
        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    child = QTreeWidgetItem(parent_item, [item, "文件夹"])
                    child.setData(0, Qt.ItemDataRole.UserRole, item_path)
                    QTreeWidgetItem(child, ["", ""])
                elif item.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif')):
                    child = QTreeWidgetItem(parent_item, [item, "图像文件"])
                    child.setData(0, Qt.ItemDataRole.UserRole, item_path)
        except PermissionError:
            pass

    def _on_tree_double_click(self, item, column):
        item_type = item.text(1)
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type in ["磁盘驱动器", "文件夹"] and item_path:
            if item.childCount() == 1 and item.child(0).text(0) == "":
                self.populate_folder(item, item_path)
            item.setExpanded(not item.isExpanded())
        elif item_type == "图像文件" and item_path:
            self.image_browser.open_image(item_path)
            self._after_image_change()

    def _on_tree_click(self, item, column):
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        if item_path:
            self.status_bar.showMessage(f"选中: {item_path}")

    def refresh_folder_tree(self):
        if hasattr(self, 'folder_tree'):
            self.folder_tree.clear()

    def show_loaded_folder(self):
        if not hasattr(self, 'folder_tree'):
            return
        self.folder_tree.clear()
        if self.image_browser.current_image_path:
            folder_path = os.path.dirname(self.image_browser.current_image_path)
            folder_name = os.path.basename(folder_path)
            root = QTreeWidgetItem(self.folder_tree, [folder_name, "文件夹"])
            root.setData(0, Qt.ItemDataRole.UserRole, folder_path)
            self.populate_folder(root, folder_path)
            root.setExpanded(True)

    # ==================================================================
    # 图像导航
    # ==================================================================
    def open_image(self):
        if self.image_browser.open_image():
            self._after_image_change()

    def open_folder(self):
        if self.image_browser.open_folder():
            self._after_image_change()

    def next_image(self):
        if self.image_browser.next_image():
            _load_image_annotation(self)
            self._after_nav()

    def previous_image(self):
        if self.image_browser.previous_image():
            _load_image_annotation(self)
            self._after_nav()

    def zoom_in(self):
        self.image_browser.zoom_in()

    def zoom_out(self):
        self.image_browser.zoom_out()

    def reset_zoom(self):
        self.image_browser.reset_zoom()

    # ==================================================================
    # 模型
    # ==================================================================
    def browse_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择模型文件", ".", "模型文件 (*.pt *.pth)")
        if path:
            self.model_path_edit.setText(path)

    def load_model(self):
        path = self.model_path_edit.text()
        if not path:
            QMessageBox.warning(self, "警告", "请先选择模型文件！")
            return
        if self.model_loader.load_model(path):
            self.status_bar.showMessage(f"模型加载成功: {os.path.basename(path)}")
            model_classes = self.model_loader.get_classes()
            if model_classes:
                model_class_list = [model_classes[i] for i in sorted(model_classes.keys())]
                self.manual_editor.class_list = model_class_list
                self.class_manager.update_ui_class_list(model_classes)
                current_folder = ""
                if self.image_browser.current_image_path:
                    current_folder = os.path.dirname(self.image_browser.current_image_path)
                else:
                    current_folder = os.path.dirname(path)
                self.class_manager.classes_file = os.path.join(current_folder, "classes.txt")
                self.class_manager.save_to_file()
                self.model_loaded = True
                self.update_annotation_list()
                self.update_annotation_prop_display()
        else:
            self.status_bar.showMessage("模型加载失败")
            QMessageBox.warning(self, "警告", "模型加载失败！")

    def _on_conf_change(self, value):
        conf = value / 100.0
        self.conf_value_label.setText(f"{conf:.2f}")
        self.model_loader.set_confidence_threshold(conf)

    def _on_iou_change(self, value):
        iou = value / 100.0
        self.iou_value_label.setText(f"{iou:.2f}")
        self.model_loader.set_iou_threshold(iou)

    # ==================================================================
    # 视觉提示
    # ==================================================================
    def start_visual_drawing(self):
        if not self.image_browser.current_image_path:
            QMessageBox.warning(self, "警告", "请先打开图像！")
            return
        self.visual_drawing = True
        self.visual_prompt_label.setText("正在绘制边界框...")
        self.start_drawing_btn.setEnabled(False)
        self.stop_drawing_btn.setEnabled(True)
        self.image_browser.toggle_crosshair(True)
        self.drawing_start = None
        self.drawing_rect = None

    def stop_visual_drawing(self):
        self.visual_drawing = False
        self.visual_prompt_label.setText("就绪")
        self.start_drawing_btn.setEnabled(True)
        self.stop_drawing_btn.setEnabled(False)
        self.image_browser.toggle_crosshair(False)
        if self.drawing_rect:
            self.image_browser.scene.removeItem(self.drawing_rect)
            self.drawing_rect = None
        if self.visual_prompts and self.has_new_prompt:
            self._save_visual_vpe()

    def _finish_visual_drawing(self, bbox):
        iw = self.image_browser.image_width
        ih = self.image_browser.image_height
        x1 = int(max(0, min(iw, bbox[0])))
        y1 = int(max(0, min(ih, bbox[1])))
        x2 = int(max(0, min(iw, bbox[2])))
        y2 = int(max(0, min(ih, bbox[3])))

        prompt = {"type": "bbox", "xyxy": [x1, y1, x2, y2]}
        tag, ok = QInputDialog.getText(self, "输入标签", "请为该视觉提示输入类别标签:")
        if not ok or not tag.strip():
            return
        tag = tag.strip()
        prompt["tag"] = tag

        self.visual_prompts.append(prompt)
        self.visual_labels.append(tag)
        self.has_new_prompt = True

        if tag not in self.manual_editor.class_list:
            self.manual_editor.class_list.append(tag)
            self.class_manager.update_ui_class_list(
                {i: cls for i, cls in enumerate(self.manual_editor.class_list)})
            self.class_manager.save_to_file()

        self._refresh_visual_prompt_list()
        self.label_engine.auto_label()
        self.drawing_start = None

    def _refresh_visual_prompt_list(self):
        self.visual_prompt_list.clear()
        for i, p in enumerate(self.visual_prompts):
            if p["type"] == "bbox":
                x1, y1, x2, y2 = p["xyxy"]
                text = f"{i+1}: 边界框 - {p['tag']} ({x1},{y1},{x2},{y2})"
            else:
                text = f"{i+1}: 掩码 - {p['tag']} ({len(p['pts'])}个点)"
            self.visual_prompt_list.addItem(text)

    def clear_visual_prompts(self):
        self.visual_prompts.clear()
        self.visual_labels.clear()
        self.visual_vpe = None
        self.has_new_prompt = True
        self._refresh_visual_prompt_list()
        self.visual_prompt_label.setText("已清除所有视觉提示")

    def _save_visual_vpe(self):
        try:
            if hasattr(self.model_loader, 'visual_vpe') and self.model_loader.visual_vpe is not None:
                self.visual_vpe = self.model_loader.visual_vpe
                self.visual_prompt_label.setText(f"VPE缓存已保存，提示数量: {len(self.visual_prompts)}")
                self.has_new_prompt = False
        except Exception as e:
            self.visual_prompt_label.setText(f"保存VPE缓存失败: {str(e)}")

    # ==================================================================
    # 标注操作 (委托给 label_engine)
    # ==================================================================
    def auto_label(self):
        self.label_engine.auto_label()

    def similar_label_auto_label(self):
        self.label_engine.similar_label_auto_label()

    def batch_label(self):
        self.label_engine.batch_label()

    def save_annotation(self):
        if self.label_exporter.export_single_annotation():
            self.status_bar.showMessage("标注保存成功")
        else:
            self.status_bar.showMessage("标注保存失败")

    def auto_save_annotation(self):
        if self.image_browser.current_image_path:
            try:
                self.label_exporter.export_single_annotation()
            except Exception as e:
                print(f"自动保存失败: {e}")

    def export_annotation(self):
        output_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if output_dir:
            if self.label_exporter.export_single_annotation(output_dir=output_dir):
                self.status_bar.showMessage("标注导出成功")
            else:
                self.status_bar.showMessage("标注导出失败")

    def batch_export(self):
        success, fail = self.label_exporter.export_batch_annotations()
        self.status_bar.showMessage(f"批量导出完成: 成功 {success} 个，失败 {fail} 个")
        QMessageBox.information(self, "批量导出完成", f"成功: {success} 个\n失败: {fail} 个")

    def delete_annotation(self):
        self.manual_editor.delete_selected()
        self.update_annotation_list()
        self.auto_save_annotation()

    def clear_annotations(self):
        self.annotation_display.clear_annotations()
        self.update_annotation_list()
        self.auto_save_annotation()

    # ==================================================================
    # 标注列表 & 属性面板
    # ==================================================================
    def _on_anno_item_click(self, item):
        index = self.annotation_list.row(item)
        annotations = self.annotation_display.get_annotations()
        if 0 <= index < len(annotations):
            self.annotation_display.select_annotation(annotations[index])
            self.update_annotation_prop_display()

    def _on_anno_row_change(self, row):
        annotations = self.annotation_display.get_annotations()
        if 0 <= row < len(annotations):
            self.annotation_display.select_annotation(annotations[row])
            self.update_annotation_prop_display()

    def update_annotation_list(self):
        self.annotation_list.clear()
        for i, anno in enumerate(self.annotation_display.get_annotations()):
            type_tag = ""
            if anno.get('segmentation') and len(anno['segmentation']) >= 3:
                type_tag = "[seg] "
            elif anno.get('keypoints') and len(anno['keypoints']) > 0:
                type_tag = "[pose] "
            text = f"{i}: {type_tag}{anno['class_name']} ({anno['confidence']:.2f})"
            self.annotation_list.addItem(QListWidgetItem(text))

    def update_annotation_prop_display(self):
        selected = self.annotation_display.selected_annotation
        if not selected:
            self.x1_edit.setText("")
            self.y1_edit.setText("")
            self.x2_edit.setText("")
            self.y2_edit.setText("")
            self.conf_edit.setText("")
            return
        x1, y1, x2, y2 = selected['bbox']
        self.x1_edit.setText(str(x1))
        self.y1_edit.setText(str(y1))
        self.x2_edit.setText(str(x2))
        self.y2_edit.setText(str(y2))
        self.conf_edit.setText(f"{selected['confidence']:.2f}")
        items = [self.prop_class_combo.itemText(i) for i in range(self.prop_class_combo.count())]
        if selected['class_name'] in items:
            self.prop_class_combo.setCurrentText(selected['class_name'])

    def update_annotation_prop(self):
        selected = self.annotation_display.selected_annotation
        if not selected:
            return
        try:
            class_name = self.prop_class_combo.currentText().strip()
            if not class_name:
                QMessageBox.warning(self, "警告", "类别名称不能为空！")
                return
            x1 = int(float(self.x1_edit.text()))
            y1 = int(float(self.y1_edit.text()))
            x2 = int(float(self.x2_edit.text()))
            y2 = int(float(self.y2_edit.text()))
            confidence = float(self.conf_edit.text())

            current_items = [self.prop_class_combo.itemText(i) for i in range(self.prop_class_combo.count())]
            if class_name not in current_items:
                self.prop_class_combo.addItem(class_name)
                self.manual_editor.class_list.append(class_name)
                self.class_manager.update_ui_class_list(
                    {i: cls for i, cls in enumerate(self.manual_editor.class_list)})
                self.class_manager.save_to_file()

            updated_items = [self.prop_class_combo.itemText(i) for i in range(self.prop_class_combo.count())]
            class_id = updated_items.index(class_name)
            self.manual_editor.current_class = class_id
            self.annotation_display.update_annotation(
                selected, bbox=[x1, y1, x2, y2],
                class_name=class_name, class_id=class_id, confidence=confidence)
            self.update_annotation_list()
            self.auto_save_annotation()
        except ValueError as e:
            QMessageBox.warning(self, "警告", f"无效的输入值：{str(e)}")

    def save_classes_to_file(self):
        """委托给 ClassManager"""
        self.class_manager.save_to_file()

    def manage_classes(self):
        """委托给 ClassManager"""
        self.class_manager.manage_classes()

    def update_all_panels(self):
        current_classes = self.manual_editor.class_list
        if current_classes:
            self.class_manager.update_ui_class_list(
                {i: cls for i, cls in enumerate(current_classes)})
        self.update_annotation_list()
        self.update_annotation_prop_display()

    # ==================================================================
    # 数据集组织
    # ==================================================================
    def browse_output_dir(self):
        output_dir = QFileDialog.getExistingDirectory(self, "选择输出目录", ".")
        if output_dir:
            self.output_dir_edit.setText(output_dir)

    def organize_dataset(self):
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录！")
            return
        try:
            train_r = float(self.train_ratio_edit.text().strip())
            val_r = float(self.val_ratio_edit.text().strip())
            test_r = float(self.test_ratio_edit.text().strip())
        except ValueError:
            QMessageBox.warning(self, "警告", "比例设置必须为数字！")
            return
        if abs(train_r + val_r + test_r - 1.0) > 1e-6:
            QMessageBox.warning(self, "警告", "数据集比例之和必须为1！")
            return
        try:
            seed = int(self.seed_edit.text().strip())
        except ValueError:
            seed = 42

        # 检查有标签的图像数量
        labeled_count = 0
        for p in self.image_browser.image_files:
            lp = os.path.splitext(p)[0] + '.txt'
            if os.path.exists(lp) and os.path.getsize(lp) > 0:
                labeled_count += 1
        if labeled_count == 0:
            QMessageBox.warning(self, "警告", "没有可组织的带有标签的图像文件！")
            return

        progress = QProgressDialog("正在组织数据集...", "取消", 0, 100, self)
        progress.setWindowTitle("数据集组织")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        def update_progress(current, total):
            if total > 0:
                progress.setValue(int(current / total * 100))
                self.status_bar.showMessage(f"正在组织数据集: {current}/{total} 个文件")
                return not progress.wasCanceled()
            return True

        ratios = {'train': train_r, 'val': val_r, 'test': test_r}
        success = self.dataset_organizer.organize_dataset(
            output_dir, ratios, seed, copy_files=True, progress_callback=update_progress)
        progress.close()

        if success:
            summary = self.dataset_organizer.get_dataset_summary(output_dir)
            bvn_dir = os.path.join(output_dir, 'datasets', 'bvn')
            blank_dir = os.path.join(output_dir, 'blank')
            msg = (
                f"数据集组织成功！\n\n"
                f"训练集: {summary['train']['images']} 张图像, {summary['train']['labels']} 个标签\n"
                f"验证集: {summary['val']['images']} 张图像, {summary['val']['labels']} 个标签\n"
                f"测试集: {summary['test']['images']} 张图像, {summary['test']['labels']} 个标签\n"
                f"空白图像: {summary['blank']['images']} 张图像（保存到blank文件夹）\n\n"
                f"数据集保存到: {bvn_dir}\n空白图像保存到: {blank_dir}"
            )
            QMessageBox.information(self, "成功", msg)
            self.status_bar.showMessage("数据集组织成功")
        else:
            QMessageBox.warning(self, "失败", "数据集组织失败！")
            self.status_bar.showMessage("数据集组织失败")

    # ==================================================================
    # 文件保存
    # ==================================================================
    def set_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存文件夹")
        if folder:
            self.save_folder = folder
            self.status_bar.showMessage(f"默认保存文件夹已设置: {folder}")

    def save_current_image(self):
        current = self.image_browser.get_current_image_path()
        if not current:
            QMessageBox.warning(self, "警告", "请先打开图像！")
            return
        if self.save_folder:
            dest = os.path.join(self.save_folder, os.path.basename(current))
            try:
                shutil.copy2(current, dest)
                self.status_bar.showMessage(f"图像保存成功: {dest}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")
        else:
            name = os.path.basename(current)
            dest, _ = QFileDialog.getSaveFileName(
                self, "保存图像", name, "图像文件 (*.png *.jpg *.jpeg *.bmp *.tif)")
            if dest:
                try:
                    shutil.copy2(current, dest)
                    self.save_folder = os.path.dirname(dest)
                    self.status_bar.showMessage(f"图像保存成功: {dest}")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")

    # ==================================================================
    # 辅助
    # ==================================================================
    def update_status_bar(self):
        info = self.image_browser.get_current_image_info()
        if info:
            msg = (f"图像: {info['filename']} | "
                   f"尺寸: {info['width']}x{info['height']} | "
                   f"{info['index']+1}/{info['total']}")
            self.status_bar.showMessage(msg)

    def show_format_converter(self):
        """打开格式转换工具对话框"""
        dialog = FormatConverterDialog(self)
        dialog.exec()

    def show_about(self):
        QMessageBox.information(
            self, "关于 YOLOE 自动标注系统",
            "YOLOE 自动标注系统\n基于 Ultralytics YOLOE 模型\n\n版本: 1.0"
        )

    # ---- 内部辅助 ----
    def _after_image_change(self):
        """打开图像/文件夹后的统一刷新（加载标注 + 刷新界面）"""
        _load_image_annotation(self)
        self.class_manager.load_from_file()
        self.update_status_bar()
        self.update_all_panels()
        self.show_loaded_folder()

    def _after_nav(self):
        """翻图后的统一刷新（不重新加载 classes.txt）"""
        self.update_status_bar()
        self.update_all_panels()


# ==================================================================
# 入口
# ==================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
