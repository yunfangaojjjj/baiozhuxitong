# YOLOE自动标注系统 - 图像浏览模块

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFileDialog, QMessageBox
from PyQt6.QtGui import QImage, QPixmap, QPainter, QCursor, QColor, QPen
from PyQt6.QtCore import Qt, QRectF, QPointF
import os
import cv2
import numpy as np

# 自定义QGraphicsView类，实现按住滚轮键平移功能
class CustomGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)  # 禁用默认的拖动模式
        
        # 平移相关属性
        self.is_middle_pressed = False
        self.last_mouse_pos = None
        self.is_left_dragging = False
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            # 中键用于平移
            self.is_middle_pressed = True
            self.last_mouse_pos = event.pos()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            # 左键用于绘制和操作标注
            self.is_left_dragging = True
            self.last_mouse_pos = event.pos()
            # 调用原始事件处理，确保scene能收到事件
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.is_middle_pressed:
            # 中键拖动平移
            current_pos = event.pos()
            delta = current_pos - self.last_mouse_pos
            
            # 平移视图
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            
            self.last_mouse_pos = current_pos
            event.accept()
        else:
            # 其他情况调用原始事件处理
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            # 中键释放
            self.is_middle_pressed = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            # 左键释放
            self.is_left_dragging = False
            # 调用原始事件处理
            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

class ImageBrowser:
    def __init__(self, graphics_view):
        """
        初始化图像浏览器
        
        Args:
            graphics_view (QGraphicsView): 用于显示图像的QGraphicsView组件
        """
        self.graphics_view = graphics_view
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        
        # 图像相关属性
        self.current_image_path = None
        self.image_files = []
        self.current_index = -1
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.zoom_step = 0.1
        
        # 图像项
        self.pixmap_item = None
        self.image_width = 0
        self.image_height = 0
        
        # 十字辅助线相关属性
        self.crosshair_h = None  # 水平辅助线
        self.crosshair_v = None  # 垂直辅助线
        self.show_crosshair = False  # 是否显示十字辅助线
        self.crosshair_color = QColor(255, 255, 0, 255)  # 十字线颜色，设置为明显的黄色
        self.crosshair_width = 3  # 十字线宽度
    
    def _get_images_from_folder(self, folder_path):
        """
        获取文件夹及其子文件夹中的所有图像文件
        
        Args:
            folder_path (str): 文件夹路径
            
        Returns:
            list: 图像文件路径列表
        """
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tif']
        image_files = []
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if os.path.splitext(file)[1].lower() in image_extensions:
                    image_files.append(os.path.join(root, file))
        
        return sorted(image_files)
    
    def open_image(self, image_path=None):
        """
        打开单张图像
        
        Args:
            image_path (str, optional): 图像文件路径，如果为None则打开文件对话框
            
        Returns:
            bool: 打开成功返回True，否则返回False
        """
        if not image_path:
            # 打开文件对话框
            file_dialog = QFileDialog()
            file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp *.tif)")
            file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
            
            if file_dialog.exec():
                image_path = file_dialog.selectedFiles()[0]
            else:
                return False
        
        # 检查文件是否存在
        if not os.path.exists(image_path):
            QMessageBox.warning(self.graphics_view, "警告", "图像文件不存在！")
            return False
        
        # 加载图像
        if self._load_image(image_path):
            # 获取当前文件夹
            folder_path = os.path.dirname(image_path)
            
            # 获取文件夹及其子文件夹中的所有图像
            self.image_files = self._get_images_from_folder(folder_path)
            
            # 更新当前索引
            self.current_index = self.image_files.index(image_path) if image_path in self.image_files else 0
            return True
        return False
    
    def open_folder(self, folder_path=None):
        """
        打开图像文件夹
        
        Args:
            folder_path (str, optional): 文件夹路径，如果为None则打开文件夹对话框
            
        Returns:
            bool: 打开成功返回True，否则返回False
        """
        if not folder_path:
            # 打开文件夹对话框
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.FileMode.Directory)
            file_dialog.setOption(QFileDialog.Option.ShowDirsOnly)
            
            if file_dialog.exec():
                folder_path = file_dialog.selectedFiles()[0]
            else:
                return False
        
        # 检查文件夹是否存在
        if not os.path.isdir(folder_path):
            QMessageBox.warning(self.graphics_view, "警告", "文件夹不存在！")
            return False
        
        # 获取文件夹及其子文件夹中的图像文件
        self.image_files = self._get_images_from_folder(folder_path)
        
        if not self.image_files:
            QMessageBox.warning(self.graphics_view, "警告", "文件夹中没有找到图像文件！")
            return False
        
        # 加载第一张图像
        self.current_index = 0
        return self._load_image(self.image_files[self.current_index])
    
    def _load_image(self, image_path):
        """
        加载图像到场景中
        
        Args:
            image_path (str): 图像文件路径
            
        Returns:
            bool: 加载成功返回True，否则返回False
        """
        try:
            # 使用OpenCV加载图像
            cv_image = cv2.imread(image_path)
            if cv_image is None:
                return False
            
            # 转换为RGB格式
            cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            
            # 获取图像尺寸
            self.image_height, self.image_width, _ = cv_image.shape
            
            # 创建QImage
            q_image = QImage(
                cv_image.data, 
                self.image_width, 
                self.image_height, 
                cv_image.strides[0], 
                QImage.Format.Format_RGB888
            )
            
            # 创建QPixmap
            pixmap = QPixmap.fromImage(q_image)
            
            # 先清除十字辅助线
            if hasattr(self, 'crosshair_h') and self.crosshair_h:
                try:
                    self.scene.removeItem(self.crosshair_h)
                except RuntimeError:
                    pass
                self.crosshair_h = None
            if hasattr(self, 'crosshair_v') and self.crosshair_v:
                try:
                    self.scene.removeItem(self.crosshair_v)
                except RuntimeError:
                    pass
                self.crosshair_v = None
            
            # 清除场景中的所有项目
            self.scene.clear()
            
            # 添加图像项
            self.pixmap_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.pixmap_item)
            
            # 创建新的十字辅助线
            self._create_crosshair()
            
            # 重置缩放和平移
            self.zoom_level = 1.0
            self.reset_view()
            
            # 更新当前图像路径
            self.current_image_path = image_path
            
            return True
        except Exception as e:
            print(f"图像加载失败: {e}")
            return False
    
    def _create_crosshair(self):
        """
        创建十字辅助线
        """
        # 清除现有十字辅助线
        if self.crosshair_h:
            self.scene.removeItem(self.crosshair_h)
        if self.crosshair_v:
            self.scene.removeItem(self.crosshair_v)
        
        # 创建水平辅助线
        self.crosshair_h = self.scene.addLine(0, 0, self.image_width, 0)
        self.crosshair_h.setPen(QPen(self.crosshair_color, self.crosshair_width, Qt.PenStyle.DotLine))
        self.crosshair_h.setZValue(999)  # 置于顶层
        self.crosshair_h.setVisible(self.show_crosshair)
        
        # 创建垂直辅助线
        self.crosshair_v = self.scene.addLine(0, 0, 0, self.image_height)
        self.crosshair_v.setPen(QPen(self.crosshair_color, self.crosshair_width, Qt.PenStyle.DotLine))
        self.crosshair_v.setZValue(999)  # 置于顶层
        self.crosshair_v.setVisible(self.show_crosshair)
    
    def update_crosshair(self, pos):
        """
        更新十字辅助线位置
        
        Args:
            pos (QPointF): 鼠标在场景中的位置
        """
        if self.crosshair_h and self.crosshair_v:
            # 更新水平辅助线位置
            self.crosshair_h.setLine(0, pos.y(), self.image_width, pos.y())
            # 更新垂直辅助线位置
            self.crosshair_v.setLine(pos.x(), 0, pos.x(), self.image_height)
    
    def toggle_crosshair(self, show=True):
        """
        显示或隐藏十字辅助线
        
        Args:
            show (bool, optional): 是否显示十字辅助线
        """
        self.show_crosshair = show
        if self.crosshair_h:
            self.crosshair_h.setVisible(show)
        if self.crosshair_v:
            self.crosshair_v.setVisible(show)
    
    def next_image(self):
        """
        显示下一张图像
        
        Returns:
            bool: 成功返回True，否则返回False
        """
        if not self.image_files or len(self.image_files) <= 1:
            return False
        
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            return self._load_image(self.image_files[self.current_index])
        return False
    
    def previous_image(self):
        """
        显示上一张图像
        
        Returns:
            bool: 成功返回True，否则返回False
        """
        if not self.image_files or len(self.image_files) <= 1:
            return False
        
        if self.current_index > 0:
            self.current_index -= 1
            return self._load_image(self.image_files[self.current_index])
        return False
    
    def zoom_in(self):
        """
        放大图像
        """
        if self.zoom_level < self.max_zoom:
            self.zoom_level += self.zoom_step
            self._apply_zoom()
    
    def zoom_out(self):
        """
        缩小图像
        """
        if self.zoom_level > self.min_zoom:
            self.zoom_level -= self.zoom_step
            self._apply_zoom()
    
    def reset_zoom(self):
        """
        重置缩放
        """
        self.zoom_level = 1.0
        self.reset_view()
    
    def reset_view(self):
        """
        重置视图，使图像居中显示
        """
        if self.pixmap_item:
            # 重置缩放
            self.zoom_level = 1.0
            
            # 重置视图变换
            self.graphics_view.resetTransform()
            
            # 调整场景大小
            self.scene.setSceneRect(QRectF(self.pixmap_item.boundingRect()))
            
            # 居中显示
            self.graphics_view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            
            # 保存当前缩放级别
            self.zoom_level = self._get_current_zoom()
    
    def _apply_zoom(self):
        """
        应用缩放变换
        """
        if self.pixmap_item:
            # 使用视图的缩放功能，而不是修改pixmap_item的transform
            self.graphics_view.resetTransform()
            self.graphics_view.scale(self.zoom_level, self.zoom_level)
    
    def _get_current_zoom(self):
        """
        获取当前缩放级别
        
        Returns:
            float: 当前缩放级别
        """
        # 从视图的transform获取缩放因子
        transform = self.graphics_view.transform()
        return transform.m11()  # 缩放因子
    
    def get_current_image_path(self):
        """
        获取当前图像路径
        
        Returns:
            str: 当前图像路径
        """
        return self.current_image_path
    
    def get_current_image_info(self):
        """
        获取当前图像信息
        
        Returns:
            dict: 包含文件名、路径、尺寸和当前索引的字典
        """
        if not self.current_image_path:
            return {}
        
        return {
            'filename': os.path.basename(self.current_image_path),
            'path': self.current_image_path,
            'width': self.image_width,
            'height': self.image_height,
            'index': self.current_index,
            'total': len(self.image_files)
        }
    
    def get_image_files(self):
        """
        获取图像文件列表
        
        Returns:
            list: 图像文件路径列表
        """
        return self.image_files
    
    def is_image_loaded(self):
        """
        检查是否有图像加载
        
        Returns:
            bool: 有图像加载返回True，否则返回False
        """
        return self.current_image_path is not None
    
    def screen_to_image_coords(self, screen_point):
        """
        将屏幕坐标转换为图像坐标
        
        Args:
            screen_point (QPoint): 屏幕坐标点
            
        Returns:
            tuple: 图像坐标 (x, y)
        """
        if not self.pixmap_item:
            return (0, 0)
        
        # 将屏幕坐标转换为场景坐标
        scene_point = self.graphics_view.mapToScene(screen_point)
        
        # 将场景坐标转换为图像坐标
        image_point = self.pixmap_item.mapFromScene(scene_point)
        
        return (int(image_point.x()), int(image_point.y()))
    
    def image_to_screen_coords(self, image_point):
        """
        将图像坐标转换为屏幕坐标
        
        Args:
            image_point (tuple): 图像坐标 (x, y)
            
        Returns:
            QPoint: 屏幕坐标点
        """
        if not self.pixmap_item:
            return QPointF(0, 0)
        
        # 将图像坐标转换为场景坐标
        scene_point = self.pixmap_item.mapToScene(QPointF(image_point[0], image_point[1]))
        
        # 将场景坐标转换为屏幕坐标
        screen_point = self.graphics_view.mapFromScene(scene_point)
        
        return screen_point
