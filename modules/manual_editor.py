# YOLOE自动标注系统 - 人工编辑模块

from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsSceneMouseEvent, QInputDialog, QComboBox, QWidget
from PyQt6.QtGui import QPen, QColor, QCursor
from PyQt6.QtCore import Qt, QPointF, QRectF
from config import Config

class ManualEditor:
    def __init__(self, annotation_display, image_browser):
        """
        初始化人工编辑模块
        
        Args:
            annotation_display (AnnotationDisplay): 标注显示模块实例
            image_browser (ImageBrowser): 图像浏览模块实例
        """
        self.annotation_display = annotation_display
        self.image_browser = image_browser
        
        # 编辑状态
        self.is_drawing = False  # 是否正在绘制新边界框
        self.drawing_start = QPointF()  # 绘制起始点
        self.drawing_rect = None  # 正在绘制的矩形
        self.resize_handle = None  # 当前调整大小的手柄
        self.move_offset = QPointF()  # 移动偏移量
        
        # 标注模式
        self.annotation_mode = False  # 是否处于标注模式（按w键切换）
        
        # 手柄大小
        self.handle_size = 12

        # 当前鼠标悬停的手柄
        self.hovered_handle = None
        
        # 可用类别列表
        self.class_list = []
        self.current_class = 0
    
    def start_drawing(self, scene_pos):
        """
        开始绘制新的边界框
        
        Args:
            scene_pos (QPointF): 绘制起始点
        """
        self.is_drawing = True
        self.drawing_start = scene_pos
        
        # 创建绘制中的矩形
        self.drawing_rect = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
        pen = QPen(QColor(255, 0, 0), Config.ANNOTATION_CONFIG['box_thickness'], Qt.PenStyle.DashLine)
        self.drawing_rect.setPen(pen)
        self.drawing_rect.setZValue(1000)  # 置于顶层
        self.annotation_display.scene.addItem(self.drawing_rect)
    
    def update_drawing(self, scene_pos):
        """
        更新正在绘制的边界框
        
        Args:
            scene_pos (QPointF): 当前鼠标位置
        """
        if self.is_drawing and self.drawing_rect:
            # 更新矩形大小
            rect = QRectF(self.drawing_start, scene_pos).normalized()
            self.drawing_rect.setRect(rect)
    
    def finish_drawing(self, scene_pos):
        """
        完成绘制边界框
        
        Args:
            scene_pos (QPointF): 绘制结束点
        """
        if self.is_drawing and self.drawing_rect:
            # 获取绘制的矩形
            rect = QRectF(self.drawing_start, scene_pos).normalized()
            
            # 检查矩形大小
            min_size = 5  # 最小边界框大小
            if rect.width() < min_size or rect.height() < min_size:
                # 矩形太小，取消绘制
                self.cancel_drawing()
                return
            
            # 弹窗输入标签类别
            if self.class_list:
                # 如果有现有类别，显示下拉选择框
                class_name, ok = QInputDialog.getItem(
                    self.image_browser.graphics_view,
                    "选择标签类别",
                    "请选择或输入标签类别:",
                    self.class_list, 
                    self.current_class, 
                    True  # 允许用户输入新类别
                )
                
                if not ok or not class_name:
                    # 用户取消或输入为空，取消绘制
                    self.cancel_drawing()
                    return
                
                # 检查是否是新类别
                if class_name not in self.class_list:
                    # 添加新类别
                    self.class_list.append(class_name)
                    class_id = len(self.class_list) - 1
                    # 更新当前类别为新添加的类别
                    self.current_class = class_id
                    # 触发主窗口保存类别到文件
                    if hasattr(self, 'main_window') and hasattr(self.main_window, 'save_classes_to_file'):
                        self.main_window.save_classes_to_file()
                else:
                    # 现有类别
                    class_id = self.class_list.index(class_name)
                    # 更新当前类别为选中的类别
                    self.current_class = class_id
            else:
                # 没有现有类别，直接输入
                class_name, ok = QInputDialog.getText(
                    self.image_browser.graphics_view,
                    "输入标签类别",
                    "请输入标签类别:"
                )
                
                if not ok or not class_name:
                    # 用户取消或输入为空，取消绘制
                    self.cancel_drawing()
                    return
                
                # 添加新类别
                self.class_list.append(class_name)
                class_id = 0
                # 更新当前类别为新添加的类别
                self.current_class = class_id
                # 触发主窗口保存类别到文件
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'save_classes_to_file'):
                    self.main_window.save_classes_to_file()
            
            # 添加新标注
            bbox = [int(rect.left()), int(rect.top()), int(rect.right()), int(rect.bottom())]
            self.annotation_display.add_annotation(bbox, class_name, class_id)
            
            # 清理绘制状态
            self.annotation_display.scene.removeItem(self.drawing_rect)
            self.drawing_rect = None
            self.is_drawing = False
            
            # 触发主窗口的自动保存功能
            # 通过信号或直接调用主窗口方法
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'auto_save_annotation'):
                self.main_window.auto_save_annotation()
    
    def cancel_drawing(self):
        """
        取消绘制边界框
        """
        if self.is_drawing and self.drawing_rect:
            self.annotation_display.scene.removeItem(self.drawing_rect)
            self.drawing_rect = None
            self.is_drawing = False
    
    def handle_mouse_press(self, event):
        """
        处理鼠标按下事件
        
        Args:
            event (QGraphicsSceneMouseEvent): 鼠标事件
        """
        scene_pos = event.scenePos()
        
        # 检查是否点击在现有标注上
        annotation = self.annotation_display.get_annotation_at_point(scene_pos)
        
        if annotation:
            # 检查是否点击在调整大小手柄上
            handle = self._get_handle_at_point(annotation, scene_pos)
            if handle is not None:
                # 开始调整大小
                self.resize_handle = handle
                self.resize_start = scene_pos
                self.original_bbox = annotation['bbox'].copy()
                # 选中该标注
                self.annotation_display.select_annotation(annotation)
            else:
                # 开始移动标注
                self.move_offset = scene_pos - QPointF(annotation['bbox'][0], annotation['bbox'][1])
                # 选中该标注
                self.annotation_display.select_annotation(annotation)
        elif self.annotation_mode:
            # 处于标注模式且未点击在标注上，开始绘制新标注
            self.start_drawing(scene_pos)
            # 取消选中所有标注
            self.annotation_display.select_annotation(None)
    
    def handle_mouse_move(self, event):
        """
        处理鼠标移动事件
        
        Args:
            event (QGraphicsSceneMouseEvent): 鼠标事件
        """
        scene_pos = event.scenePos()
        
        # 更新十字辅助线位置（如果处于标注模式）
        if self.annotation_mode:
            self.image_browser.update_crosshair(scene_pos)
        
        if self.is_drawing:
            # 更新绘制中的矩形
            self.update_drawing(scene_pos)
        elif self.resize_handle is not None:
            # 调整现有标注大小
            annotation = self.annotation_display.selected_annotation
            if annotation:
                self._resize_annotation(annotation, scene_pos)
        elif self.move_offset.x() != 0 or self.move_offset.y() != 0:
            # 移动现有标注
            annotation = self.annotation_display.selected_annotation
            if annotation:
                self._move_annotation(annotation, scene_pos)
        else:
            # 更新鼠标悬停状态
            self._update_hover_state(scene_pos)
    
    def handle_mouse_release(self, event):
        """
        处理鼠标释放事件
        
        Args:
            event (QGraphicsSceneMouseEvent): 鼠标事件
        """
        scene_pos = event.scenePos()
        
        if self.is_drawing:
            # 完成绘制
            self.finish_drawing(scene_pos)
        elif self.resize_handle is not None:
            # 结束调整大小
            self.resize_handle = None
        elif self.move_offset.x() != 0 or self.move_offset.y() != 0:
            # 结束移动
            self.move_offset = QPointF()
    
    def _get_handle_at_point(self, annotation, point):
        """
        检查点是否在调整大小的手柄上
        
        Args:
            annotation (dict): 标注项
            point (QPointF): 检查点
            
        Returns:
            str: 手柄名称，如果不在手柄上则返回None
        """
        x1, y1, x2, y2 = annotation['bbox']
        
        # 定义手柄区域
        handles = {
            'top_left': QRectF(x1 - self.handle_size, y1 - self.handle_size, self.handle_size * 2, self.handle_size * 2),
            'top_right': QRectF(x2 - self.handle_size, y1 - self.handle_size, self.handle_size * 2, self.handle_size * 2),
            'bottom_left': QRectF(x1 - self.handle_size, y2 - self.handle_size, self.handle_size * 2, self.handle_size * 2),
            'bottom_right': QRectF(x2 - self.handle_size, y2 - self.handle_size, self.handle_size * 2, self.handle_size * 2),
            'left': QRectF(x1 - self.handle_size, (y1 + y2) / 2 - self.handle_size, self.handle_size * 2, self.handle_size * 2),
            'right': QRectF(x2 - self.handle_size, (y1 + y2) / 2 - self.handle_size, self.handle_size * 2, self.handle_size * 2),
            'top': QRectF((x1 + x2) / 2 - self.handle_size, y1 - self.handle_size, self.handle_size * 2, self.handle_size * 2),
            'bottom': QRectF((x1 + x2) / 2 - self.handle_size, y2 - self.handle_size, self.handle_size * 2, self.handle_size * 2)
        }
        
        # 检查点是否在任何手柄上
        for handle_name, handle_rect in handles.items():
            if handle_rect.contains(point):
                return handle_name
        
        return None
    
    def _update_hover_state(self, point):
        """
        更新鼠标悬停状态
        
        Args:
            point (QPointF): 当前鼠标位置
        """
        # 检查是否悬停在标注或手柄上
        annotation = self.annotation_display.get_annotation_at_point(point)
        
        if annotation:
            # 检查是否悬停在手柄上
            handle = self._get_handle_at_point(annotation, point)
            if handle:
                # 设置相应的鼠标光标
                cursor = self._get_cursor_for_handle(handle)
                self.image_browser.graphics_view.setCursor(cursor)
                self.hovered_handle = handle
            else:
                # 设置移动光标
                self.image_browser.graphics_view.setCursor(Qt.CursorShape.SizeAllCursor)
                self.hovered_handle = None
        else:
            # 恢复默认光标
            self.image_browser.graphics_view.setCursor(Qt.CursorShape.ArrowCursor)
            self.hovered_handle = None
    
    def _get_cursor_for_handle(self, handle):
        """
        获取手柄对应的光标形状
        
        Args:
            handle (str): 手柄名称
            
        Returns:
            Qt.CursorShape: 光标形状
        """
        cursor_map = {
            'top_left': Qt.CursorShape.SizeFDiagCursor,
            'top_right': Qt.CursorShape.SizeBDiagCursor,
            'bottom_left': Qt.CursorShape.SizeBDiagCursor,
            'bottom_right': Qt.CursorShape.SizeFDiagCursor,
            'left': Qt.CursorShape.SizeHorCursor,
            'right': Qt.CursorShape.SizeHorCursor,
            'top': Qt.CursorShape.SizeVerCursor,
            'bottom': Qt.CursorShape.SizeVerCursor
        }
        
        return cursor_map.get(handle, Qt.CursorShape.ArrowCursor)
    
    def _resize_annotation(self, annotation, new_pos):
        """
        调整标注大小
        
        Args:
            annotation (dict): 标注项
            new_pos (QPointF): 当前鼠标位置
        """
        x1, y1, x2, y2 = self.original_bbox
        dx = new_pos.x() - self.resize_start.x()
        dy = new_pos.y() - self.resize_start.y()
        
        # 根据调整大小的手柄更新边界框
        if self.resize_handle == 'top_left':
            x1 += dx
            y1 += dy
        elif self.resize_handle == 'top_right':
            x2 += dx
            y1 += dy
        elif self.resize_handle == 'bottom_left':
            x1 += dx
            y2 += dy
        elif self.resize_handle == 'bottom_right':
            x2 += dx
            y2 += dy
        elif self.resize_handle == 'left':
            x1 += dx
        elif self.resize_handle == 'right':
            x2 += dx
        elif self.resize_handle == 'top':
            y1 += dy
        elif self.resize_handle == 'bottom':
            y2 += dy
        
        # 获取图像尺寸
        image_width = self.image_browser.image_width
        image_height = self.image_browser.image_height
        
        # 确保边界框不会超出图像范围
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(image_width, x2)
        y2 = min(image_height, y2)
        
        # 确保边界框不会变得太小（最小尺寸为5像素）
        min_size = 5
        if self.resize_handle in ['top_left', 'bottom_right', 'top_right', 'bottom_left']:
            # 对角调整，确保宽高不小于最小尺寸
            if abs(x2 - x1) < min_size:
                if self.resize_handle in ['top_left', 'bottom_left']:
                    x1 = x2 - min_size
                else:
                    x2 = x1 + min_size
            if abs(y2 - y1) < min_size:
                if self.resize_handle in ['top_left', 'top_right']:
                    y1 = y2 - min_size
                else:
                    y2 = y1 + min_size
        elif self.resize_handle in ['left', 'right']:
            # 水平调整，确保宽度不小于最小尺寸
            if abs(x2 - x1) < min_size:
                if self.resize_handle == 'left':
                    x1 = x2 - min_size
                else:
                    x2 = x1 + min_size
        elif self.resize_handle in ['top', 'bottom']:
            # 垂直调整，确保高度不小于最小尺寸
            if abs(y2 - y1) < min_size:
                if self.resize_handle == 'top':
                    y1 = y2 - min_size
                else:
                    y2 = y1 + min_size
        
        # 确保坐标顺序正确
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # 更新标注
        new_bbox = [int(x1), int(y1), int(x2), int(y2)]
        self.annotation_display.update_annotation(annotation, bbox=new_bbox)
    
    def _move_annotation(self, annotation, new_pos):
        """
        移动标注

        Args:
            annotation (dict): 标注项
            new_pos (QPointF): 当前鼠标位置
        """
        # 计算新的边界框位置
        new_x1 = int(new_pos.x() - self.move_offset.x())
        new_y1 = int(new_pos.y() - self.move_offset.y())

        x1, y1, x2, y2 = annotation['bbox']
        width = x2 - x1
        height = y2 - y1
        dx = new_x1 - x1
        dy = new_y1 - y1

        new_bbox = [new_x1, new_y1, new_x1 + width, new_y1 + height]

        # 如果有分割多边形，同步平移所有顶点
        new_segmentation = None
        if annotation.get('segmentation') and len(annotation['segmentation']) >= 3:
            new_segmentation = [[p[0] + dx, p[1] + dy] for p in annotation['segmentation']]

        self.annotation_display.update_annotation(
            annotation, bbox=new_bbox, segmentation=new_segmentation
        )
    
    def delete_selected(self):
        """
        删除选中的标注
        """
        selected = self.annotation_display.selected_annotation
        if selected:
            self.annotation_display.remove_annotation(selected)
    
    def update_class(self, class_id, class_name):
        """
        更新当前类别
        
        Args:
            class_id (int): 类别ID
            class_name (str): 类别名称
        """
        self.current_class = class_id
        
        # 更新选中标注的类别
        selected = self.annotation_display.selected_annotation
        if selected:
            self.annotation_display.update_annotation(
                selected, 
                class_id=class_id, 
                class_name=class_name
            )
    
    def set_class_list(self, class_list):
        """
        设置可用类别列表
        
        Args:
            class_list (list): 类别名称列表
        """
        self.class_list = class_list
        if class_list and self.current_class >= len(class_list):
            self.current_class = 0
    
    def add_new_class(self, class_name):
        """
        添加新类别
        
        Args:
            class_name (str): 新类别名称
        """
        if class_name not in self.class_list:
            self.class_list.append(class_name)
    
    def edit_annotation_class(self):
        """
        编辑选中标注的类别
        """
        selected = self.annotation_display.selected_annotation
        if not selected or not self.class_list:
            return
        
        # 显示类别选择对话框
        class_name, ok = QInputDialog.getItem(
            self.image_browser.graphics_view,
            "编辑类别",
            "选择类别:",
            self.class_list, 
            self.class_list.index(selected['class_name']) if selected['class_name'] in self.class_list else 0, 
            False
        )
        
        if ok:
            class_id = self.class_list.index(class_name)
            self.annotation_display.update_annotation(
                selected, 
                class_name=class_name, 
                class_id=class_id
            )
    
    def create_class_combobox(self, parent_widget):
        """
        创建类别选择下拉框
        
        Args:
            parent_widget (QWidget): 父窗口组件
            
        Returns:
            QComboBox: 类别选择下拉框
        """
        combobox = QComboBox(parent_widget)
        combobox.addItems(self.class_list)
        combobox.setCurrentIndex(self.current_class)
        
        # 连接信号
        combobox.currentIndexChanged.connect(lambda index: self.update_class(index, self.class_list[index]))
        
        return combobox
    
    def cancel_edit(self):
        """
        取消当前编辑操作
        """
        if self.is_drawing:
            self.cancel_drawing()
        
        self.resize_handle = None
        self.move_offset = QPointF()
    
    def handle_key_press(self, event):
        """
        处理键盘事件
        
        Args:
            event (QKeyEvent): 键盘事件
        """
        key = event.key()
        
        # 删除键删除选中标注
        if key == Qt.Key.Key_Delete:
            self.delete_selected()
        # W键切换标注模式
        elif key == Qt.Key.Key_W:
            self.annotation_mode = not self.annotation_mode
            # 更新鼠标光标
            if self.annotation_mode:
                self.image_browser.graphics_view.setCursor(Qt.CursorShape.CrossCursor)
                self.image_browser.toggle_crosshair(True)  # 显示十字辅助线
            else:
                self.image_browser.graphics_view.setCursor(Qt.CursorShape.ArrowCursor)
                self.image_browser.toggle_crosshair(False)  # 隐藏十字辅助线
        # 方向键微调选中标注
        elif self.annotation_display.selected_annotation:
            annotation = self.annotation_display.selected_annotation
            bbox = annotation['bbox'].copy()
            step = 1  # 微调步长
            
            if key == Qt.Key.Key_Left:
                bbox[0] -= step
                bbox[2] -= step
            elif key == Qt.Key.Key_Right:
                bbox[0] += step
                bbox[2] += step
            elif key == Qt.Key.Key_Up:
                bbox[1] -= step
                bbox[3] -= step
            elif key == Qt.Key.Key_Down:
                bbox[1] += step
                bbox[3] += step
            
            self.annotation_display.update_annotation(annotation, bbox=bbox)
    
    def get_current_state(self):
        """
        获取当前编辑状态
        
        Returns:
            dict: 当前编辑状态
        """
        return {
            'is_drawing': self.is_drawing,
            'has_selected_annotation': self.annotation_display.is_annotation_selected(),
            'current_class': self.current_class,
            'class_list_length': len(self.class_list)
        }
    
    def reset(self):
        """
        重置编辑状态
        """
        self.cancel_edit()
        self.annotation_display.select_annotation(None)
        self.image_browser.graphics_view.setCursor(Qt.CursorShape.ArrowCursor)
