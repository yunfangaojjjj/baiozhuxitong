# YOLOE自动标注系统 - UI构建模块

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSplitter, QMenuBar, QMenu, QStatusBar, QToolBar, QSlider,
    QLineEdit, QGroupBox, QComboBox, QListWidget, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QScrollArea, QListWidgetItem,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction

from config import Config
from modules.image_browser import CustomGraphicsView


class UIBuilder:
    """负责构建主窗口的所有 UI 面板、菜单和工具栏"""

    def __init__(self, mw):
        """
        Args:
            mw (MainWindow): 主窗口引用，UI 控件作为属性直接挂载到 mw 上
        """
        self.mw = mw

    def build(self):
        """构建完整的 UI 布局"""
        mw = self.mw
        mw.setWindowTitle(Config.GUI_CONFIG['window_title'])
        mw.resize(Config.GUI_CONFIG['window_size'][0], Config.GUI_CONFIG['window_size'][1])

        # 从样式模块应用样式
        from modules.styles import setup_styling
        setup_styling(mw)

        # 主控件和布局
        central_widget = QWidget()
        mw.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧面板
        left_panel = self._create_left_panel()

        # 中央图像显示区域
        mw.graphics_view = CustomGraphicsView()
        mw.graphics_view.setMinimumSize(640, 480)

        # 右侧面板
        right_panel = self._create_right_panel()

        # 分割器布局
        splitter1 = QSplitter(Qt.Orientation.Horizontal)
        splitter1.addWidget(left_panel)
        splitter1.addWidget(mw.graphics_view)
        splitter1.addWidget(right_panel)
        splitter1.setSizes([340, 760, 300])
        left_panel.setMinimumWidth(300)
        right_panel.setMinimumWidth(280)
        main_layout.addWidget(splitter1)

        # 菜单栏、工具栏、状态栏
        self._create_menu_bar()
        self._create_tool_bar()
        mw.status_bar = QStatusBar()
        mw.setStatusBar(mw.status_bar)
        mw.status_bar.showMessage("就绪")

    # ------------------------------------------------------------------
    # 左侧面板
    # ------------------------------------------------------------------
    def _create_left_panel(self):
        mw = self.mw
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # ---- 文件夹树 ----
        self._build_folder_tree_group(left_layout)

        # ---- 模型设置 ----
        self._build_model_group(left_layout)

        # ---- 视觉提示 ----
        self._build_visual_prompt_group(left_layout)

        # ---- 自动标注按钮 ----
        mw.auto_label_btn = QPushButton("自动标注")
        mw.auto_label_btn.setObjectName("auto_label_btn")
        mw.auto_label_btn.clicked.connect(mw.auto_label)
        left_layout.addWidget(mw.auto_label_btn)

        mw.similar_label_btn = QPushButton("同类标签自动标注")
        mw.similar_label_btn.clicked.connect(mw.similar_label_auto_label)
        left_layout.addWidget(mw.similar_label_btn)

        # ---- 标注列表 ----
        self._build_annotation_group(left_layout)

        # ---- AI 多边形 ----
        mw.ai_polygon_btn = QPushButton("AI 多边形")
        mw.ai_polygon_btn.setObjectName("ai_polygon_btn")
        mw.ai_polygon_btn.setToolTip(
            "交互式 AI 多边形标注（SAM）\n"
            "左键=前景点  右键=背景点\n"
            "Enter=确认  Backspace=撤销  Esc=退出")
        mw.ai_polygon_btn.clicked.connect(mw.toggle_ai_polygon)
        left_layout.addWidget(mw.ai_polygon_btn)

        left_layout.addStretch()
        left_scroll.setWidget(left_panel)
        return left_scroll

    def _build_folder_tree_group(self, layout):
        mw = self.mw
        folder_group = QGroupBox("文件系统")
        folder_layout = QVBoxLayout(folder_group)

        mw.folder_tree = QTreeWidget()
        mw.folder_tree.setHeaderLabels(["名称", "类型"])
        mw.folder_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        mw.folder_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        mw.folder_tree.header().resizeSection(1, 80)
        # 限制高度，把空间让给标注列表
        mw.folder_tree.setMaximumHeight(220)
        folder_layout.addWidget(mw.folder_tree)

        btn_layout = QHBoxLayout()
        open_btn = QPushButton("打开文件夹")
        open_btn.clicked.connect(mw.open_folder)
        btn_layout.addWidget(open_btn)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(mw.refresh_folder_tree)
        btn_layout.addWidget(refresh_btn)
        folder_layout.addLayout(btn_layout)

        layout.addWidget(folder_group)

    def _build_model_group(self, layout):
        mw = self.mw
        model_group = QGroupBox("模型设置")
        model_layout = QVBoxLayout(model_group)

        mw.model_path_edit = QLineEdit()
        mw.model_path_edit.setPlaceholderText("模型权重路径")
        model_layout.addWidget(mw.model_path_edit)

        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(mw.browse_model)
        model_layout.addWidget(browse_btn)

        mw.load_model_btn = QPushButton("加载模型")
        mw.load_model_btn.clicked.connect(mw.load_model)
        model_layout.addWidget(mw.load_model_btn)

        # 置信度阈值
        conf_group = QVBoxLayout()
        conf_group.addWidget(QLabel("置信度阈值:"))
        mw.conf_slider = QSlider(Qt.Orientation.Horizontal)
        mw.conf_slider.setMinimum(10)
        mw.conf_slider.setMaximum(100)
        mw.conf_slider.setValue(int(Config.MODEL_CONFIG['confidence_threshold'] * 100))
        mw.conf_value_label = QLabel(f"{Config.MODEL_CONFIG['confidence_threshold']:.2f}")
        conf_slider_layout = QHBoxLayout()
        conf_slider_layout.addWidget(mw.conf_slider)
        conf_slider_layout.addWidget(mw.conf_value_label)
        conf_group.addLayout(conf_slider_layout)
        model_layout.addLayout(conf_group)

        # IoU 阈值
        iou_group = QVBoxLayout()
        iou_group.addWidget(QLabel("IoU阈值:"))
        mw.iou_slider = QSlider(Qt.Orientation.Horizontal)
        mw.iou_slider.setMinimum(10)
        mw.iou_slider.setMaximum(100)
        mw.iou_slider.setValue(int(Config.MODEL_CONFIG['iou_threshold'] * 100))
        mw.iou_value_label = QLabel(f"{Config.MODEL_CONFIG['iou_threshold']:.2f}")
        iou_slider_layout = QHBoxLayout()
        iou_slider_layout.addWidget(mw.iou_slider)
        iou_slider_layout.addWidget(mw.iou_value_label)
        iou_group.addLayout(iou_slider_layout)
        model_layout.addLayout(iou_group)

        layout.addWidget(model_group)

    def _build_visual_prompt_group(self, layout):
        mw = self.mw
        vp_group = QVBoxLayout()
        vp_group.addWidget(QLabel("视觉提示:"))

        mw.start_drawing_btn = QPushButton("开始绘制视觉提示")
        mw.start_drawing_btn.clicked.connect(mw.start_visual_drawing)
        vp_group.addWidget(mw.start_drawing_btn)

        mw.stop_drawing_btn = QPushButton("停止绘制")
        mw.stop_drawing_btn.clicked.connect(mw.stop_visual_drawing)
        mw.stop_drawing_btn.setEnabled(False)
        vp_group.addWidget(mw.stop_drawing_btn)

        vp_group.addWidget(QLabel("当前视觉提示:"))
        mw.visual_prompt_list = QListWidget()
        vp_list_layout = QVBoxLayout()
        vp_list_layout.addWidget(mw.visual_prompt_list)

        clear_btn = QPushButton("清除视觉提示")
        clear_btn.clicked.connect(mw.clear_visual_prompts)
        vp_list_layout.addWidget(clear_btn)
        vp_group.addLayout(vp_list_layout)

        mw.visual_prompt_label = QLabel("就绪")
        vp_group.addWidget(mw.visual_prompt_label)
        layout.addLayout(vp_group)

    # ------------------------------------------------------------------
    # 右侧面板
    # ------------------------------------------------------------------
    def _create_right_panel(self):
        mw = self.mw
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        self._build_property_group(right_layout)
        self._build_batch_group(right_layout)
        self._build_dataset_group(right_layout)

        right_layout.addStretch()
        right_scroll.setWidget(right_panel)
        return right_scroll

    def _build_annotation_group(self, layout):
        mw = self.mw
        group = QGroupBox("标注列表")
        group_layout = QVBoxLayout(group)

        mw.annotation_list = QListWidget()
        # 伸展占据左侧剩余空间
        mw.annotation_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        group_layout.addWidget(mw.annotation_list)

        btn_layout = QHBoxLayout()
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(mw.delete_annotation)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(mw.clear_annotations)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(clear_btn)
        group_layout.addLayout(btn_layout)
        layout.addWidget(group)

    def _build_property_group(self, layout):
        mw = self.mw
        group = QGroupBox("标注属性")
        prop_layout = QVBoxLayout(group)

        # 类别
        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel("类别:"))
        mw.prop_class_combo = QComboBox()
        mw.prop_class_combo.setEditable(True)
        class_layout.addWidget(mw.prop_class_combo)
        manage_btn = QPushButton("管理类别")
        manage_btn.clicked.connect(mw.manage_classes)
        class_layout.addWidget(manage_btn)
        prop_layout.addLayout(class_layout)

        # 边界框坐标
        prop_layout.addWidget(QLabel("边界框坐标:"))
        x1y1_layout = QHBoxLayout()
        x1y1_layout.addWidget(QLabel("x1:"))
        mw.x1_edit = QLineEdit()
        x1y1_layout.addWidget(mw.x1_edit)
        x1y1_layout.addWidget(QLabel("y1:"))
        mw.y1_edit = QLineEdit()
        x1y1_layout.addWidget(mw.y1_edit)
        prop_layout.addLayout(x1y1_layout)

        x2y2_layout = QHBoxLayout()
        x2y2_layout.addWidget(QLabel("x2:"))
        mw.x2_edit = QLineEdit()
        x2y2_layout.addWidget(mw.x2_edit)
        x2y2_layout.addWidget(QLabel("y2:"))
        mw.y2_edit = QLineEdit()
        x2y2_layout.addWidget(mw.y2_edit)
        prop_layout.addLayout(x2y2_layout)

        # 置信度
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("置信度:"))
        mw.conf_edit = QLineEdit()
        conf_layout.addWidget(mw.conf_edit)
        prop_layout.addLayout(conf_layout)

        update_btn = QPushButton("更新属性")
        update_btn.clicked.connect(mw.update_annotation_prop)
        prop_layout.addWidget(update_btn)

        layout.addWidget(group)

    def _build_batch_group(self, layout):
        mw = self.mw
        group = QGroupBox("批量模型标注")
        batch_layout = QVBoxLayout(group)

        # 权重选择
        w_layout = QHBoxLayout()
        w_layout.addWidget(QLabel("权重:"))
        mw.batch_weights_edit = QLineEdit()
        mw.batch_weights_edit.setPlaceholderText("选择 .pt 权重文件")
        w_layout.addWidget(mw.batch_weights_edit)
        browse_w = QPushButton("浏览")
        browse_w.clicked.connect(mw.browse_batch_weights)
        w_layout.addWidget(browse_w)
        batch_layout.addLayout(w_layout)

        load_btn = QPushButton("加载模型")
        load_btn.clicked.connect(mw.load_batch_model)
        batch_layout.addWidget(load_btn)

        mw.batch_model_status = QLabel("未加载模型")
        mw.batch_model_status.setWordWrap(True)
        batch_layout.addWidget(mw.batch_model_status)

        # 推理参数
        p_layout = QHBoxLayout()
        p_layout.addWidget(QLabel("置信度:"))
        mw.batch_conf_edit = QLineEdit("0.25")
        p_layout.addWidget(mw.batch_conf_edit)
        p_layout.addWidget(QLabel("IoU:"))
        mw.batch_iou_edit = QLineEdit("0.45")
        p_layout.addWidget(mw.batch_iou_edit)
        batch_layout.addLayout(p_layout)

        run_btn = QPushButton("批量标注")
        run_btn.setObjectName("convert_btn")
        run_btn.clicked.connect(mw.batch_label)
        batch_layout.addWidget(run_btn)

        layout.addWidget(group)

    def _build_dataset_group(self, layout):
        mw = self.mw
        group = QGroupBox("数据集组织")
        ds_layout = QVBoxLayout(group)

        # 输出目录
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("输出目录:"))
        mw.output_dir_edit = QLineEdit()
        mw.output_dir_edit.setPlaceholderText("选择输出目录")
        out_layout.addWidget(mw.output_dir_edit)
        ds_layout.addLayout(out_layout)

        browse_btn = QPushButton("浏览输出目录")
        browse_btn.clicked.connect(mw.browse_output_dir)
        ds_layout.addWidget(browse_btn)

        # 比例设置
        ds_layout.addWidget(QLabel("数据集比例:"))

        for name, default in [("训练集", "0.7"), ("验证集", "0.2"), ("测试集", "0.1")]:
            rl = QHBoxLayout()
            rl.addWidget(QLabel(f"{name}:"))
            edit = QLineEdit(default)
            rl.addWidget(edit)
            rl.addWidget(QLabel("%"))
            ds_layout.addLayout(rl)
            if name == "训练集":
                mw.train_ratio_edit = edit
            elif name == "验证集":
                mw.val_ratio_edit = edit
            else:
                mw.test_ratio_edit = edit

        # 随机种子
        seed_layout = QHBoxLayout()
        seed_layout.addWidget(QLabel("随机种子:"))
        mw.seed_edit = QLineEdit("42")
        seed_layout.addWidget(mw.seed_edit)
        ds_layout.addLayout(seed_layout)

        mw.organize_dataset_btn = QPushButton("组织数据集")
        mw.organize_dataset_btn.setObjectName("organize_dataset_btn")
        mw.organize_dataset_btn.clicked.connect(mw.organize_dataset)
        ds_layout.addWidget(mw.organize_dataset_btn)

        layout.addWidget(group)

    # ------------------------------------------------------------------
    # 菜单栏
    # ------------------------------------------------------------------
    def _create_menu_bar(self):
        mw = self.mw
        menu_bar = mw.menuBar()

        # ---- 文件 ----
        file_menu = menu_bar.addMenu("文件")

        actions = [
            ("打开图像", "Ctrl+O", mw.open_image),
            ("打开文件夹", "Ctrl+Shift+O", mw.open_folder),
            ("保存标注", "Ctrl+S", mw.save_annotation),
            ("导出标注", "Ctrl+E", mw.export_annotation),
            # Space 由 keyPressEvent 处理（保存当前图像并跳到下一张），这里不占用快捷键
            ("保存图像", None, mw.save_current_image),
            ("设置保存文件夹", None, mw.set_save_folder),
            ("批量导出", "Ctrl+Shift+E", mw.batch_export),
            ("退出", "Ctrl+Q", mw.close),
        ]
        for name, shortcut, handler in actions:
            action = QAction(name, mw)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(handler)
            file_menu.addAction(action)

        # ---- 编辑 ----
        edit_menu = menu_bar.addMenu("编辑")
        for name, shortcut, handler in [
            ("AI 多边形标注", "Ctrl+P", mw.toggle_ai_polygon),
            ("删除标注", "Delete", mw.delete_annotation),
            ("清空标注", None, mw.clear_annotations),
        ]:
            action = QAction(name, mw)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(handler)
            edit_menu.addAction(action)

        # ---- 视图 ----
        view_menu = menu_bar.addMenu("视图")
        for name, shortcut, handler in [
            ("放大", "Ctrl++", mw.zoom_in),
            ("缩小", "Ctrl+-", mw.zoom_out),
            ("重置缩放", "Ctrl+0", mw.reset_zoom),
        ]:
            action = QAction(name, mw)
            action.setShortcut(shortcut)
            action.triggered.connect(handler)
            view_menu.addAction(action)

        # ---- 工具 ----
        tools_menu = menu_bar.addMenu("工具")
        format_convert_action = QAction("YOLO 格式转换 (TXT ↔ JSON)", mw)
        format_convert_action.triggered.connect(mw.show_format_converter)
        tools_menu.addAction(format_convert_action)

        # ---- 帮助 ----
        help_menu = menu_bar.addMenu("帮助")
        about_action = QAction("关于", mw)
        about_action.triggered.connect(mw.show_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    # 工具栏
    # ------------------------------------------------------------------
    def _create_tool_bar(self):
        mw = self.mw
        tool_bar = mw.addToolBar("工具")
        tool_bar.setIconSize(QSize(24, 24))

        for name, handler in [
            ("打开图像", mw.open_image),
            ("打开文件夹", mw.open_folder),
        ]:
            action = QAction(name, mw)
            action.triggered.connect(handler)
            tool_bar.addAction(action)

        tool_bar.addSeparator()

        for name, handler in [
            ("上一张", mw.previous_image),
            ("下一张", mw.next_image),
        ]:
            action = QAction(name, mw)
            action.triggered.connect(handler)
            tool_bar.addAction(action)

        tool_bar.addSeparator()

        for name, handler in [
            ("自动标注", mw.auto_label),
            ("AI 多边形", mw.toggle_ai_polygon),
        ]:
            action = QAction(name, mw)
            action.triggered.connect(handler)
            tool_bar.addAction(action)

        tool_bar.addSeparator()

        for name, handler in [
            ("保存标注", mw.save_annotation),
            ("导出标注", mw.export_annotation),
        ]:
            action = QAction(name, mw)
            action.triggered.connect(handler)
            tool_bar.addAction(action)

        tool_bar.addSeparator()

        format_action = QAction("格式转换", mw)
        format_action.triggered.connect(mw.show_format_converter)
        tool_bar.addAction(format_action)
