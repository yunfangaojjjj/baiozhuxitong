# AI 标注系统 - 样式模块

from PyQt6.QtGui import QPalette, QColor, QFont


def setup_styling(window):
    """
    设置应用程序样式（深色主题）

    Args:
        window (QMainWindow): 主窗口实例
    """
    # 主色调
    background_color = QColor(30, 30, 35)
    surface_color = QColor(40, 40, 45)
    accent_color = QColor(0, 150, 255)
    accent_hover = QColor(0, 170, 255)
    text_color = QColor(240, 240, 240)
    text_secondary = QColor(180, 180, 180)
    border_color = QColor(60, 60, 65)
    success_color = QColor(0, 200, 100)
    warning_color = QColor(255, 165, 0)
    error_color = QColor(255, 80, 80)

    # 设置调色板
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, background_color)
    palette.setColor(QPalette.ColorRole.WindowText, text_color)
    palette.setColor(QPalette.ColorRole.Base, surface_color)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 50))
    palette.setColor(QPalette.ColorRole.ToolTipBase, accent_color)
    palette.setColor(QPalette.ColorRole.ToolTipText, text_color)
    palette.setColor(QPalette.ColorRole.Text, text_color)
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 50))
    palette.setColor(QPalette.ColorRole.ButtonText, text_color)
    palette.setColor(QPalette.ColorRole.BrightText, error_color)
    palette.setColor(QPalette.ColorRole.Link, accent_color)
    palette.setColor(QPalette.ColorRole.Highlight, accent_color)
    palette.setColor(QPalette.ColorRole.HighlightedText, text_color)
    window.setPalette(palette)

    # 设置字体
    font = QFont("Microsoft YaHei UI", 10)
    window.setFont(font)

    # 全局样式表
    window.setStyleSheet("""
        /* 主窗口 */
        QMainWindow {
            background-color: #1e1e23;
        }

        /* 面板和容器 */
        QWidget {
            background-color: #1e1e23;
            color: #f0f0f0;
            font-family: 'Microsoft YaHei UI', 'Segoe UI', Arial, sans-serif;
        }

        /* 组框 */
        QGroupBox {
            background-color: #28282d;
            border: 1px solid #3c3c44;
            border-radius: 5px;
            margin-top: 5px;
            padding: 20px 15px 15px 15px;
        }

        QGroupBox::title {
            subcontrol-origin: padding;
            subcontrol-position: top left;
            left: 10px;
            top: 8px;
            padding: 0 5px;
            background-color: #28282d;
            color: #ffffff;
            font-weight: bold;
            font-size: 8pt;
            white-space: nowrap;
        }

        /* 按钮 */
        QPushButton {
            background-color: #3c3c44;
            color: #f0f0f0;
            border: 1px solid #505058;
            border-radius: 6px;
            padding: 8px 12px;
            font-weight: 500;
        }

        QPushButton:hover {
            background-color: #0096ff;
            border-color: #0096ff;
            color: white;
        }

        QPushButton:pressed {
            background-color: #007acc;
        }

        QPushButton:disabled {
            background-color: #2d2d32;
            color: #888;
            border-color: #444;
        }

        /* 重要按钮样式 */
        QPushButton#auto_label_btn, QPushButton#organize_dataset_btn {
            background-color: #00c853;
            border-color: #00c853;
        }

        QPushButton#auto_label_btn:hover, QPushButton#organize_dataset_btn:hover {
            background-color: #00e676;
        }

        QPushButton#auto_label_btn:pressed, QPushButton#organize_dataset_btn:pressed {
            background-color: #00b248;
        }

        /* 转换按钮样式 */
        QPushButton#convert_btn {
            background-color: #0096ff;
            border-color: #0096ff;
            color: white;
            font-weight: bold;
            font-size: 10pt;
        }

        QPushButton#convert_btn:hover {
            background-color: #00bfff;
            border-color: #00bfff;
        }

        QPushButton#convert_btn:pressed {
            background-color: #007acc;
        }

        /* AI 多边形按钮样式 */
        QPushButton#ai_polygon_btn {
            background-color: #7c4dff;
            border-color: #7c4dff;
            color: white;
            font-weight: bold;
        }

        QPushButton#ai_polygon_btn:hover {
            background-color: #9575ff;
            border-color: #9575ff;
        }

        QPushButton#ai_polygon_btn:pressed {
            background-color: #651fff;
        }

        /* 行编辑器 */
        QLineEdit {
            background-color: #323238;
            color: #f0f0f0;
            border: 1px solid #484850;
            border-radius: 4px;
            padding: 6px 10px;
            selection-background-color: #0096ff;
            selection-color: white;
        }

        QLineEdit:focus {
            border-color: #0096ff;
            background-color: #38383f;
        }

        /* 下拉框 */
        QComboBox {
            background-color: #323238;
            color: #f0f0f0;
            border: 1px solid #484850;
            border-radius: 4px;
            padding: 6px 10px;
        }

        QComboBox:focus {
            border-color: #0096ff;
        }

        QComboBox::drop-down {
            background-color: #38383f;
            border: 1px solid #484850;
            border-radius: 0 4px 4px 0;
        }

        QComboBox::down-arrow {
            image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23f0f0f0'%3E%3Cpath d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
            width: 12px;
            height: 12px;
        }

        /* 滑块 */
        QSlider::groove:horizontal {
            background: #323238;
            height: 6px;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            background: #0096ff;
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }

        QSlider::handle:horizontal:hover {
            background: #00bfff;
        }

        /* 列表部件 */
        QListWidget {
            background-color: #323238;
            color: #f0f0f0;
            border: 1px solid #484850;
            border-radius: 4px;
            selection-background-color: #0096ff;
            selection-color: white;
        }

        QListWidget::item {
            padding: 8px 12px;
            border-bottom: 1px solid #3c3c44;
        }

        QListWidget::item:hover {
            background-color: #3c3c44;
        }

        /* 树部件 */
        QTreeWidget {
            background-color: #323238;
            color: #f0f0f0;
            border: 1px solid #484850;
            border-radius: 4px;
            selection-background-color: #0096ff;
            selection-color: white;
        }

        QTreeWidget::branch {
            background: transparent;
        }

        QTreeWidget::item {
            padding: 6px 0;
        }

        QTreeWidget::item:hover {
            background-color: #3c3c44;
        }

        /* 状态栏 */
        QStatusBar {
            background-color: #28282d;
            color: #b0b0b0;
            border-top: 1px solid #3c3c44;
            padding: 4px 12px;
        }

        /* 菜单 */
        QMenuBar {
            background-color: #28282d;
            color: #f0f0f0;
            border-bottom: 1px solid #3c3c44;
        }

        QMenuBar::item {
            background-color: transparent;
            color: #f0f0f0;
            padding: 8px 16px;
        }

        QMenuBar::item:selected {
            background-color: #3c3c44;
        }

        QMenu {
            background-color: #28282d;
            color: #f0f0f0;
            border: 1px solid #3c3c44;
            border-radius: 4px;
        }

        QMenu::item {
            background-color: transparent;
            padding: 8px 24px;
            border-radius: 2px;
        }

        QMenu::item:selected {
            background-color: #0096ff;
            color: white;
        }

        /* 工具栏 */
        QToolBar {
            background-color: #28282d;
            border-bottom: 1px solid #3c3c44;
            spacing: 8px;
        }

        /* 分隔器 */
        QSplitter::handle {
            background-color: #3c3c44;
            width: 4px;
            margin: 5px 0;
        }

        QSplitter::handle:hover {
            background-color: #0096ff;
        }

        QSplitter::handle:horizontal {
            width: 4px;
        }

        QSplitter::handle:vertical {
            height: 4px;
        }

        /* 标签 */
        QLabel {
            color: #f0f0f0;
        }

        /* 滚动条 */
        QScrollBar:vertical {
            background: #2d2d32;
            width: 10px;
            margin: 0;
        }

        QScrollBar::handle:vertical {
            background: #555;
            border-radius: 5px;
            min-height: 30px;
        }

        QScrollBar::handle:vertical:hover {
            background: #666;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: none;
        }

        QScrollBar:horizontal {
            background: #2d2d32;
            height: 10px;
            margin: 0;
        }

        QScrollBar::handle:horizontal {
            background: #555;
            border-radius: 5px;
            min-width: 30px;
        }

        QScrollBar::handle:horizontal:hover {
            background: #666;
        }

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            background: none;
        }
    """)
