# GUI 冒烟测试：offscreen 构建主窗口，验证 AI 多边形 UI 集成
# 运行: D:/anaconda/envs/yoloe/python.exe smoke_test_ai_polygon.py
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication  # noqa: E402
from app import MainWindow  # noqa: E402


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()

    # 验证 AI 多边形相关控件与方法存在
    assert hasattr(w, "ai_polygon_btn"), "缺少 ai_polygon_btn"
    assert hasattr(w, "ai_polygon_loader"), "缺少 ai_polygon_loader"
    assert hasattr(w, "ai_polygon_editor"), "缺少 ai_polygon_editor"
    assert hasattr(w, "toggle_ai_polygon"), "缺少 toggle_ai_polygon"
    assert hasattr(w.ai_polygon_editor, "add_point"), "缺少 add_point"
    assert hasattr(w.ai_polygon_editor, "confirm"), "缺少 confirm"
    assert hasattr(w.ai_polygon_editor, "undo_last_point"), "缺少 undo_last_point"

    print(f"AI 多边形按钮: '{w.ai_polygon_btn.text()}'")
    print(f"SAM 默认权重: {w.ai_polygon_loader.weights_path or '(未加载) '}")
    print("=== 冒烟测试通过: 主窗口构建正常, AI 多边形 UI 集成完整 ===")
    w.close()
    app.quit()


if __name__ == "__main__":
    main()
