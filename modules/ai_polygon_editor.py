# AI 标注系统 - AI 多边形交互模块（对标 Labelme 的 AI Polygon）
#
# 交互状态机：
#   - 左键单击 = 前景点（绿色），实时出分割预览
#   - 右键单击 = 背景点（红色），排除误分割区域
#   - Backspace  = 撤销上一个点
#   - Enter      = 确认当前预览，生成正式标注（可连续标注）
#   - Esc        = 退出 AI 多边形模式

import cv2

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QBrush, QColor, QPen, QPolygonF
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPolygonItem, QInputDialog

from config import Config


class AIPolygonEditor:
    """AI 多边形交互状态机，挂载在主窗口上"""

    def __init__(self, mw):
        """
        Args:
            mw (MainWindow): 主窗口引用
        """
        self.mw = mw
        self.active = False          # 是否处于 AI 多边形模式
        self.points = []             # [[x, y, label], ...] label: 1=前景 0=背景
        self.point_items = []        # 场景中的提示点图形项
        self.preview_item = None     # 预览多边形图形项
        self.current_mask = None     # 最近一次分割掩码

        cfg = Config.AI_POLYGON_CONFIG
        self.fg_color = cfg['foreground_point_color']
        self.bg_color = cfg['background_point_color']
        self.point_radius = cfg['point_radius']
        self.preview_line_color = cfg['preview_line_color']
        self.preview_fill_alpha = cfg['preview_fill_alpha']

    # ------------------------------------------------------------------
    # 模式进入 / 退出
    # ------------------------------------------------------------------
    def enter(self):
        """
        进入 AI 多边形模式

        Returns:
            tuple: (bool, str) 是否成功与提示信息
        """
        mw = self.mw
        if not mw.image_browser.is_image_loaded():
            return False, "请先打开图像！"

        # 若正在视觉提示绘制，先停止
        if getattr(mw, 'visual_drawing', False):
            mw.stop_visual_drawing()

        # 懒加载 SAM 模型
        if not mw.ai_polygon_loader.is_loaded():
            ok, msg = mw.ai_polygon_loader.load_model()
            if not ok:
                return False, msg

        self.active = True
        self.points = []
        self.current_mask = None
        return True, "AI 多边形: 左键=前景点 右键=背景点 Enter=确认 Esc=退出"

    def exit(self):
        """退出 AI 多边形模式并清理预览"""
        if not self.active:
            return
        self.active = False
        self.clear_preview()
        self.points = []
        self.current_mask = None

    def clear_preview(self):
        """清除所有提示点与预览图形项（保留正式标注）"""
        scene = self.mw.image_browser.scene
        for item in self.point_items:
            try:
                scene.removeItem(item)
            except RuntimeError:
                pass
        self.point_items = []

        if self.preview_item is not None:
            try:
                scene.removeItem(self.preview_item)
            except RuntimeError:
                pass
            self.preview_item = None

    # ------------------------------------------------------------------
    # 点操作
    # ------------------------------------------------------------------
    def add_point(self, scene_pos, is_foreground=True):
        """
        添加一个提示点并触发实时分割

        Args:
            scene_pos (QPointF): 场景坐标（与图像像素坐标一致）
            is_foreground (bool): True=前景点 False=背景点
        """
        if not self.active:
            return

        image_browser = self.mw.image_browser
        w, h = image_browser.image_width, image_browser.image_height
        x = int(max(0, min(w - 1, scene_pos.x())))
        y = int(max(0, min(h - 1, scene_pos.y())))
        label = 1 if is_foreground else 0

        self.points.append([x, y, label])

        # 显示提示点
        color = QColor(*(self.fg_color if is_foreground else self.bg_color))
        item = QGraphicsEllipseItem(
            x - self.point_radius, y - self.point_radius,
            self.point_radius * 2, self.point_radius * 2)
        item.setPen(QPen(color, 2))
        item.setBrush(QBrush(color))
        item.setZValue(1000)
        image_browser.scene.addItem(item)
        self.point_items.append(item)

        self._update_mask()

    def undo_last_point(self):
        """撤销最后一个提示点，返回是否还有可撤销项"""
        if not self.points:
            return False
        self.points.pop()
        if self.point_items:
            item = self.point_items.pop()
            try:
                self.mw.image_browser.scene.removeItem(item)
            except RuntimeError:
                pass
        if self.points:
            self._update_mask()
        else:
            self.current_mask = None
            self._update_preview([])
        return True

    # ------------------------------------------------------------------
    # 分割与预览
    # ------------------------------------------------------------------
    def _load_bgr_image(self):
        """读取当前图像（BGR），失败返回 None"""
        path = self.mw.image_browser.get_current_image_path()
        if not path:
            return None
        return cv2.imread(path)

    def _update_mask(self):
        """
        用当前提示点更新掩码与预览

        策略: 前景点交给 SAM 交互式分割; 背景点优先作为负点提示传给模型
        (官网 SAM2 权重负点有效), 模型负点无响应时由 SAMLoader 自动回退
        为掩码 flood-fill 挖除。
        """
        if not self.active or not self.points:
            return

        image = self._load_bgr_image()
        if image is None:
            return

        fg_points = [[p[0], p[1]] for p in self.points if p[2] == 1]
        bg_points = [[p[0], p[1]] for p in self.points if p[2] == 0]

        # 没有前景点则无法分割（只点背景点无意义）
        if not fg_points:
            return

        mask = self.mw.ai_polygon_loader.predict_mask(image, fg_points, bg_points or None)
        if mask is None:
            return

        self.current_mask = mask
        polygon = self.mw.ai_polygon_loader.mask_to_polygon(mask)
        self._update_preview(polygon)

    def _update_preview(self, polygon):
        """更新预览多边形图形项"""
        scene = self.mw.image_browser.scene

        if self.preview_item is not None:
            try:
                scene.removeItem(self.preview_item)
            except RuntimeError:
                pass
            self.preview_item = None

        if not polygon:
            return

        qpoly = QPolygonF([QPointF(float(p[0]), float(p[1])) for p in polygon])
        item = QGraphicsPolygonItem(qpoly)
        color = QColor(*self.preview_line_color)
        item.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
        fill = QColor(*self.preview_line_color)
        fill.setAlpha(self.preview_fill_alpha)
        item.setBrush(QBrush(fill))
        item.setZValue(900)
        scene.addItem(item)
        self.preview_item = item

    # ------------------------------------------------------------------
    # 确认生成标注
    # ------------------------------------------------------------------
    def confirm(self):
        """
        确认当前预览，生成正式标注（类别选择 + 自动保存）

        Returns:
            bool: 是否成功生成
        """
        if not self.active or self.current_mask is None:
            return False

        polygon = self.mw.ai_polygon_loader.mask_to_polygon(self.current_mask)
        if len(polygon) < 3:
            return False

        mw = self.mw

        # 选择 / 输入类别（复用 manual_editor 的类别流程）
        class_name, ok = self._ask_class()
        if not ok or not class_name:
            return False
        class_name = class_name.strip()

        class_list = mw.manual_editor.class_list
        if class_name not in class_list:
            class_list.append(class_name)
            class_id = len(class_list) - 1
            mw.class_manager.update_ui_class_list(
                {i: c for i, c in enumerate(class_list)})
            mw.class_manager.save_to_file()
        else:
            class_id = class_list.index(class_name)

        # 生成标注（bbox 由显示层从多边形自动计算）
        mw.annotation_display.add_annotation(
            bbox=None, class_name=class_name, class_id=class_id,
            confidence=1.0, segmentation=polygon)
        mw.update_annotation_list()
        mw.auto_save_annotation()

        # 清空本次交互，保持模式以便连续标注
        self.clear_preview()
        self.points = []
        self.current_mask = None
        return True

    def _ask_class(self):
        """
        弹出类别选择框，返回 (class_name, ok)

        有现成类别时用下拉选择（可输入新类别），否则直接文本输入。
        """
        mw = self.mw
        class_list = mw.manual_editor.class_list
        if class_list:
            return QInputDialog.getItem(
                mw, "选择标签类别", "请选择或输入标签类别:",
                class_list, mw.manual_editor.current_class, True)
        return QInputDialog.getText(mw, "输入标签类别", "请输入标签类别:")
