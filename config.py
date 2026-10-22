# YOLOE自动标注系统配置文件

# 导入torch以检查设备
import torch
import os

class Config:
    # 模型配置
    MODEL_CONFIG = {
        'default_weights_path': '',  # 默认模型权重路径
        'confidence_threshold': 0.3,  # 置信度阈值
        'iou_threshold': 0.5,  # NMS IoU阈值
        'device': 'cuda' if torch.cuda.is_available() else 'cpu'  # 推理设备
    }
    
    # 标注配置
    ANNOTATION_CONFIG = {
        'default_label': 'object',  # 默认标签
        'box_color': (0, 255, 0),  # 默认边界框颜色
        'selected_box_color': (255, 0, 0),  # 选中边界框颜色
        'box_thickness': 2,  # 边界框线宽
        'text_color': (255, 255, 255),  # 文本颜色
        'text_bg_color': (0, 0, 0),  # 文本背景颜色
        'text_size': 2.5,  # 文本大小
        'keypoint_radius': 4,  # 关键点圆点半径
        'keypoint_thickness': 2,  # 关键点轮廓线宽
        'skeleton_thickness': 2,  # 骨架连线线宽
        'keypoint_visible_color': (0, 255, 0),  # 完全可见关键点颜色
        'keypoint_occluded_color': (255, 165, 0),  # 遮挡关键点颜色
        'keypoint_invisible_color': (128, 128, 128),  # 不可见关键点颜色
        'skeleton_color': (0, 200, 255),  # 骨架连线颜色
        'show_keypoint_labels': True,  # 是否显示关键点名称标签
        # 分割(Seg)标注配置
        'seg_line_color': (0, 255, 0),  # 分割多边形边框颜色
        'seg_fill_alpha': 80,  # 分割多边形填充透明度 (0-255)
        'seg_line_thickness': 2  # 分割多边形线宽
    }
    
    # YOLO Pose 关键点配置（COCO 17 关键点）
    POSE_CONFIG = {
        'num_keypoints': 17,
        'keypoint_names': [
            'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
        ],
        # COCO 骨架连接，使用 0-based 索引
        'skeleton_connections': [
            [15, 13], [13, 11], [16, 14], [14, 12],  # 腿部
            [11, 12], [5, 11], [6, 12], [5, 6],       # 髋部/躯干
            [5, 7], [6, 8], [7, 9], [8, 10],          # 手臂
            [1, 2], [0, 1], [0, 2], [1, 3], [2, 4], [3, 5], [4, 6]  # 面部
        ],
        # 按类别自定义骨架连接规则
        # 'star_connections' 表示以指定关键点为中心，向其它所有可见关键点放射状连线
        # 索引为 0-based，例如 center_point=3 表示第 4 个点
        'class_skeleton_rules': {
            # 类别 0：以第 4 个点（0-based 索引 3）为中心，连接其它可见点
            0: {'star_connections': 3},
            # 类别 1：以第 3 个点（0-based 索引 2）为中心，连接其它可见点
            1: {'star_connections': 2}
        }
    }
    
    # GUI配置
    GUI_CONFIG = {
        'window_title': 'YOLOE自动标注系统',  # 窗口标题
        'window_size': (1280, 720),  # 窗口大小
        'icon_path': '',  # 图标路径
        'stylesheet_path': '',  # 样式表路径
        'zoom_step': 0.1,  # 缩放步长
        'min_zoom': 0.1,  # 最小缩放比例
        'max_zoom': 5.0,  # 最大缩放比例
        'auto_save': True  # 自动保存选项
    }
    
    # 导出配置
    EXPORT_CONFIG = {
        'default_export_dir': '',  # 默认导出目录
        'yolo_format': True,  # 是否使用YOLO格式
        'export_confidence': True  # 是否导出置信度
    }
    
    # 快捷键配置
    SHORTCUTS = {
        'next_image': 'Right',  # 下一张图像
        'prev_image': 'Left',  # 上一张图像
        'zoom_in': 'Ctrl++',  # 放大
        'zoom_out': 'Ctrl+-',  # 缩小
        'reset_zoom': 'Ctrl+0',  # 重置缩放
        'save_annotation': 'Ctrl+S',  # 保存标注
        'delete_box': 'Delete',  # 删除边界框
        'add_box': 'A',  # 添加边界框
        'toggle_auto_label': 'L'  # 切换自动标注
    }

    # AI 多边形配置（交互式 SAM 分割，对标 Labelme 的 AI Polygon）
    AI_POLYGON_CONFIG = {
        # 推理设备（默认与模型配置一致）
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        # 默认 SAM 权重路径（ultralytics 官网 SAM2 Hiera-Tiny，约 74MB，
        # 官方正/负点提示均有效；备选 sam2.1_t.pt 负点响应弱，
        # 或 MobileSAM models/mobile_sam.pt 约 40MB CPU 更快但负点响应弱）
        'default_weights_path': os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'models', 'sam2_t.pt'),
        'foreground_point_color': (0, 255, 0),   # 前景点颜色（绿色）
        'background_point_color': (255, 0, 0),   # 背景点颜色（红色）
        'point_radius': 6,                        # 提示点半径
        'preview_line_color': (0, 200, 255),      # 预览多边形线颜色
        'preview_fill_alpha': 80,                 # 预览多边形填充透明度 (0-255)
        'polygon_epsilon_ratio': 0.002,           # approxPolyDP 简化容差（相对轮廓周长比例）
        'max_polygon_points': 500,                # 简化后多边形最大点数（超出则均匀抽稀）
        'min_polygon_area': 50,                   # 最小多边形面积（过滤噪点）
        'min_preview_area': 20                    # 最小预览面积（过小视为未分割到目标）
    }
