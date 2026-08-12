# 测试 YOLO Pose 显示功能（按类别放射状连接）
import sys
import os
import numpy as np
import cv2

from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt

from modules.annotation_display import AnnotationDisplay
from modules.label_exporter import LabelExporter
from config import Config


def create_test_image(image_path, width=640, height=480):
    """创建一张测试图像"""
    img = np.ones((height, width, 3), dtype=np.uint8) * 200
    cv2.imwrite(image_path, img)


def create_pose_label(label_path):
    """
    模拟实际场景创建 YOLO Pose 格式标注文件
    类别 0：4 个关键点，第 4 个点为中心连接其它点
    类别 1：3 个关键点，第 3 个点为中心连接其它点
    类别 2：普通检测框，无关键点
    """
    lines = []
    
    # 类别 0：4 个关键点（0-based 索引 3 即第 4 个点为中心）
    # 边界框
    bbox0 = [0, 0.685103, 0.199027, 0.111861, 0.194439]
    # 4 个关键点（归一化坐标）
    kp0 = [
        [0.702859, 0.242688, 2],
        [0.636275, 0.275289, 2],
        [0.646928, 0.107629, 2],
        [0.662908, 0.197280, 2],  # 第 4 个点，中心
    ]
    parts0 = [str(v) for v in bbox0]
    for kp in kp0:
        parts0.extend([f"{kp[0]:.6f}", f"{kp[1]:.6f}", str(int(kp[2]))])
    lines.append(" ".join(parts0))
    
    # 类别 1：3 个关键点（0-based 索引 2 即第 3 个点为中心）
    bbox1 = [1, 0.269620, 0.565201, 0.177557, 0.142045]
    kp1 = [
        [0.348633, 0.547737, 2],
        [0.187944, 0.506986, 2],
        [0.314009, 0.573351, 2],  # 第 3 个点，中心
    ]
    parts1 = [str(v) for v in bbox1]
    for kp in kp1:
        parts1.extend([f"{kp[0]:.6f}", f"{kp[1]:.6f}", str(int(kp[2]))])
    lines.append(" ".join(parts1))
    
    # 类别 2：普通检测框，无关键点
    lines.append("2 0.459606 0.558215 0.051491 0.023286")
    
    with open(label_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def test_parse():
    """测试解析功能"""
    print("=== 测试 Pose 标注解析 ===")
    detections = LabelExporter.parse_pose_label_file(
        'test_data/pose.txt', 640, 480, class_list=['class_0', 'class_1', 'class_2']
    )
    print(f"解析到 {len(detections)} 个目标")
    for det in detections:
        print(f"  class_id: {det['class_id']}, class: {det['class_name']}, bbox: {det['bbox']}")
        print(f"  keypoints count: {len(det['keypoints'])}")
    return detections


def test_display(detections):
    """测试显示功能"""
    print("\n=== 测试 Pose 标注显示 ===")
    app = QApplication(sys.argv)
    
    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    
    # 加载图像作为背景
    cv_image = cv2.imread('test_data/image.jpg')
    cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    h, w, _ = cv_image.shape
    q_image = QImage(cv_image.data, w, h, cv_image.strides[0], QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(q_image)
    scene.addPixmap(pixmap)
    
    # 创建标注显示
    display = AnnotationDisplay(scene)
    display.load_detections(detections)
    
    print(f"标注数量: {len(display.get_annotations())}")
    for anno in display.get_annotations():
        print(f"  class_id: {anno['class_id']}, bbox: {anno['bbox']}")
        print(f"  keypoints: {len(anno['keypoints'])}")
        print(f"  keypoint_items: {len(anno['keypoint_items'])}")
        print(f"  skeleton_items: {len(anno['skeleton_items'])}")
        print(f"  keypoint_label_items: {len(anno['keypoint_label_items'])}")
    
    # 验证
    annos = display.get_annotations()
    assert len(annos) == 3, "标注数量应为 3"
    
    # 类别 0：4 个关键点，中心点索引 3 连接其它 3 个可见点，应得到 3 条线
    anno0 = annos[0]
    assert anno0['class_id'] == 0
    assert len(anno0['keypoints']) == 4
    assert len(anno0['skeleton_items']) == 3, f"类别 0 骨架连线数应为 3，实际 {len(anno0['skeleton_items'])}"
    
    # 类别 1：3 个关键点，中心点索引 2 连接其它 2 个可见点，应得到 2 条线
    anno1 = annos[1]
    assert anno1['class_id'] == 1
    assert len(anno1['keypoints']) == 3
    assert len(anno1['skeleton_items']) == 2, f"类别 1 骨架连线数应为 2，实际 {len(anno1['skeleton_items'])}"
    
    # 类别 2：无关键点，无线
    anno2 = annos[2]
    assert anno2['class_id'] == 2
    assert len(anno2['keypoints']) == 0
    assert len(anno2['skeleton_items']) == 0
    
    print("\n显示测试通过！")
    return app, view, display


def main():
    os.makedirs('test_data', exist_ok=True)
    create_test_image('test_data/image.jpg')
    create_pose_label('test_data/pose.txt')
    
    detections = test_parse()
    app, view, display = test_display(detections)
    
    print("\n测试完成，所有检查通过。")


if __name__ == '__main__':
    main()
