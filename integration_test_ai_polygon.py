# 集成测试：AI 多边形完整链路（交互 -> SAM 分割 -> 生成标注 -> YOLO-seg 导出）
# 运行: D:/anaconda/envs/yoloe/python.exe integration_test_ai_polygon.py
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PyQt6.QtCore import QPointF  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from app import MainWindow  # noqa: E402


def make_image(path):
    img = np.full((320, 480, 3), 30, dtype=np.uint8)
    cv2.rectangle(img, (120, 90), (320, 230), (200, 180, 100), -1)
    cv2.imwrite(path, img)
    return path


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()

    img_path = make_image("test_data/integration_test.png")
    assert w.image_browser.open_image(img_path), "打开图像失败"
    print("[1] 打开图像 OK")

    # 进入 AI 多边形模式（懒加载 SAM 模型）
    ok, msg = w.ai_polygon_editor.enter()
    assert ok, f"进入模式失败: {msg}"
    assert w.ai_polygon_editor.active
    print(f"[2] 进入 AI 多边形模式 OK ({msg})")

    # 添加前景点 -> 实时分割
    w.ai_polygon_editor.add_point(QPointF(220, 160), is_foreground=True)
    assert w.ai_polygon_editor.current_mask is not None, "未生成掩码"
    assert len(w.ai_polygon_editor.point_items) == 1
    assert w.ai_polygon_editor.preview_item is not None, "无预览多边形"
    print(f"[3] 前景点分割 OK, 掩码面积={int(w.ai_polygon_editor.current_mask.sum())}")

    # 添加背景点 -> 掩码更新
    w.ai_polygon_editor.add_point(QPointF(400, 70), is_foreground=False)
    assert len(w.ai_polygon_editor.points) == 2
    print("[4] 背景点 OK, 点数:", len(w.ai_polygon_editor.points))

    # 撤销背景点
    assert w.ai_polygon_editor.undo_last_point()
    assert len(w.ai_polygon_editor.points) == 1
    print("[5] 撤销 OK")

    # 确认生成标注（monkeypatch 类别弹框）
    w.ai_polygon_editor._ask_class = lambda: ("object", True)
    assert w.ai_polygon_editor.confirm(), "确认失败"
    annos = w.annotation_display.get_annotations()
    assert len(annos) == 1, f"标注数错误: {len(annos)}"
    seg = annos[0].get("segmentation", [])
    assert len(seg) >= 3, f"多边形点数不足: {len(seg)}"
    assert annos[0]["class_name"] == "object"
    print(f"[6] 确认生成标注 OK: class={annos[0]['class_name']}, 顶点={len(seg)}")

    # 模式保持活动（可连续标注），预览已清空
    assert w.ai_polygon_editor.active
    assert w.ai_polygon_editor.preview_item is None
    print("[7] 连续标注状态 OK")

    # 导出 YOLO-seg 标签并校验
    out_dir = "test_data/export"
    assert w.label_exporter.export_single_annotation(image_path=img_path, output_dir=out_dir)
    label_path = os.path.join(out_dir, "integration_test.txt")
    assert os.path.exists(label_path), "标签文件未生成"
    with open(label_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    parts = content.split()
    assert len(parts) >= 7 and (len(parts) - 1) % 2 == 0, f"YOLO-seg 格式异常: {content[:80]}"
    # 坐标应为归一化 0-1
    coords = [float(v) for v in parts[1:]]
    assert all(0.0 <= v <= 1.0 for v in coords), "坐标未归一化"
    print(f"[8] YOLO-seg 导出 OK: {content[:60]}...")

    # 退出模式
    w.ai_polygon_editor.exit()
    assert not w.ai_polygon_editor.active
    print("[9] 退出模式 OK")

    print("\n=== 集成测试全部通过 ===")
    w.close()
    app.quit()


if __name__ == "__main__":
    main()
