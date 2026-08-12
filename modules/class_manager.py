# YOLOE自动标注系统 - 类别管理模块

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLineEdit, QMessageBox, QInputDialog,
)


class ClassManager:
    """管理标注类别（增删改查 + classes.txt 文件读写）"""

    def __init__(self, mw):
        """
        Args:
            mw (MainWindow): 主窗口引用
        """
        self.mw = mw
        self.classes_file = None

    # ------------------------------------------------------------------
    # 文件 I/O
    # ------------------------------------------------------------------
    def load_from_file(self):
        """从当前图片所在文件夹的 classes.txt 加载类别"""
        classes = []
        current_folder = ""
        if self.mw.image_browser.current_image_path:
            current_folder = os.path.dirname(self.mw.image_browser.current_image_path)

        self.classes_file = os.path.join(current_folder, "classes.txt")

        if current_folder and os.path.exists(self.classes_file):
            try:
                with open(self.classes_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            classes.append(line)
            except Exception as e:
                print(f"加载类别文件失败: {e}")

        self.mw.manual_editor.class_list = classes
        self.update_ui_class_list({i: cls for i, cls in enumerate(classes)})

    def save_to_file(self):
        """将当前类别保存到 classes.txt"""
        if not self.classes_file:
            return
        try:
            with open(self.classes_file, 'w', encoding='utf-8') as f:
                for cls in self.mw.manual_editor.class_list:
                    f.write(f"{cls}\n")
        except Exception as e:
            print(f"保存类别文件失败: {e}")

    # ------------------------------------------------------------------
    # UI 同步
    # ------------------------------------------------------------------
    def update_ui_class_list(self, classes):
        """同步类别到下拉框和 manual_editor"""
        mw = self.mw
        class_list = [classes[i] for i in sorted(classes.keys())]
        mw.prop_class_combo.clear()
        mw.prop_class_combo.addItems(class_list)
        mw.manual_editor.set_class_list(class_list)

    # ------------------------------------------------------------------
    # 管理对话框
    # ------------------------------------------------------------------
    def manage_classes(self):
        """打开类别管理对话框"""
        mw = self.mw
        dialog = QDialog(mw)
        dialog.setWindowTitle("管理类别")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        class_list_widget = QListWidget()
        class_list_widget.addItems(mw.manual_editor.class_list)
        layout.addWidget(class_list_widget)

        new_class_edit = QLineEdit()
        new_class_edit.setPlaceholderText("输入新类别名称")
        layout.addWidget(new_class_edit)

        btn_layout = QHBoxLayout()

        add_btn = QPushButton("添加类别")
        add_btn.clicked.connect(lambda: self._add_class(new_class_edit, class_list_widget))
        btn_layout.addWidget(add_btn)

        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(lambda: self._delete_class(class_list_widget))
        btn_layout.addWidget(del_btn)

        rename_btn = QPushButton("重命名")
        rename_btn.clicked.connect(lambda: self._rename_class(class_list_widget))
        btn_layout.addWidget(rename_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        dialog.exec()

    # ------------------------------------------------------------------
    # 增 / 删 / 改
    # ------------------------------------------------------------------
    def _add_class(self, edit_widget, list_widget):
        mw = self.mw
        class_name = edit_widget.text().strip()
        if not class_name:
            QMessageBox.warning(mw, "警告", "类别名称不能为空！")
            return
        if class_name in mw.manual_editor.class_list:
            QMessageBox.warning(mw, "警告", "该类别已存在！")
            return

        # 注意：YOLO 类别 ID 是位置式的（class_id = 列表下标），
        # 所以新类别必须追加到末尾，绝不能 sort()——否则已有标注的 ID 会全部错位。
        mw.manual_editor.class_list.append(class_name)

        self._refresh_after_change(list_widget)
        edit_widget.clear()
        self.save_to_file()
        mw.status_bar.showMessage(f"已添加类别: {class_name}")

    def _delete_class(self, list_widget):
        mw = self.mw
        selected = list_widget.selectedItems()
        if not selected:
            QMessageBox.warning(mw, "警告", "请先选中要删除的类别！")
            return

        class_name = selected[0].text()
        annotations = mw.annotation_display.get_annotations()
        used_count = sum(1 for a in annotations if a['class_name'] == class_name)

        if used_count > 0:
            reply = QMessageBox.question(
                mw, "确认删除",
                f"该类别 '{class_name}' 正在被 {used_count} 个标注使用。确定要删除吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # 注意：删除中间类别会使后续类别的位置式 ID 前移。
        # 这是 YOLO 位置式类别格式的固有限制——如需稳定 ID，应在导出前确认类别顺序。
        mw.manual_editor.class_list.remove(class_name)
        self._refresh_after_change(list_widget)

        # 更新使用该类别的标注
        for anno in annotations:
            if anno['class_name'] == class_name:
                if mw.manual_editor.class_list:
                    mw.annotation_display.update_annotation(
                        anno, class_name=mw.manual_editor.class_list[0], class_id=0)
                else:
                    mw.annotation_display.remove_annotation(anno)

        mw.update_annotation_list()
        self.save_to_file()
        mw.auto_save_annotation()
        mw.status_bar.showMessage(f"已删除类别: {class_name}")

    def _rename_class(self, list_widget):
        mw = self.mw
        selected = list_widget.selectedItems()
        if not selected:
            QMessageBox.warning(mw, "警告", "请先选中要重命名的类别！")
            return

        old_name = selected[0].text()
        new_name, ok = QInputDialog.getText(mw, "重命名类别", "输入新类别名称:", text=old_name)
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        if new_name == old_name:
            return
        if new_name in mw.manual_editor.class_list:
            QMessageBox.warning(mw, "警告", "该类别名称已存在！")
            return

        index = mw.manual_editor.class_list.index(old_name)
        mw.manual_editor.class_list[index] = new_name
        # 保持原位（不 sort），否则位置式 class_id 会错位
        self._refresh_after_change(list_widget)

        for anno in mw.annotation_display.get_annotations():
            if anno['class_name'] == old_name:
                new_id = mw.manual_editor.class_list.index(new_name)
                mw.annotation_display.update_annotation(anno, class_name=new_name, class_id=new_id)

        mw.update_annotation_list()
        self.save_to_file()
        mw.auto_save_annotation()
        mw.status_bar.showMessage(f"类别 '{old_name}' 已重命名为 '{new_name}'")

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    def _refresh_after_change(self, list_widget):
        """类别变更后刷新 UI"""
        mw = self.mw
        self.update_ui_class_list({i: cls for i, cls in enumerate(mw.manual_editor.class_list)})
        list_widget.clear()
        list_widget.addItems(mw.manual_editor.class_list)
