# 测试 AI 多边形功能（SAM 点提示分割 → 简化多边形）
# 运行: D:/anaconda/envs/yoloe/python.exe test_ai_polygon.py

import sys
import os

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.sam_loader import SAMLoader  # noqa: E402


def create_test_image(path, width=480, height=320):
    """创建测试图像：深色背景 + 一个亮色矩形（模拟目标）"""
    img = np.full((height, width, 3), 30, dtype=np.uint8)
    # 目标矩形（亮色）
    cv2.rectangle(img, (120, 90), (320, 230), (200, 180, 100), -1)
    # 干扰物（另一个小矩形，用于负点测试）
    cv2.rectangle(img, (360, 40), (440, 110), (180, 90, 90), -1)
    cv2.imwrite(path, img)
    return img


def main():
    # ---- 1. 模型加载 ----
    loader = SAMLoader()
    ok, msg = loader.load_model()
    print(f"[1] 模型加载: {msg}")
    assert ok, "SAM 模型加载失败"
    assert loader.is_loaded()

    # ---- 2. 创建测试图 ----
    test_img_path = "test_data/ai_polygon_test.png"
    os.makedirs("test_data", exist_ok=True)
    image = create_test_image(test_img_path)
    h, w = image.shape[:2]
    print(f"[2] 测试图像: {w}x{h}")

    # ---- 3. 前景点分割（点在大矩形中心） ----
    fg = [[220, 160]]
    mask = loader.predict_mask(image, fg)
    assert mask is not None, "掩码预测返回 None"
    assert mask.shape == (h, w), f"掩码尺寸错误: {mask.shape}"

    fg_area = int(mask.sum())
    print(f"[3] 前景点分割: 掩码面积 = {fg_area} 像素")
    assert fg_area > 1000, "掩码面积过小，分割失败"

    # 掩码应主要覆盖大矩形区域（120,90)-(320,230)
    target_rect_area = (320 - 120) * (230 - 90)
    overlap = int(mask[90:230, 120:320].sum())
    print(f"    目标矩形内掩码像素: {overlap} / 矩形面积 {target_rect_area}")
    assert overlap > target_rect_area * 0.5, "掩码与目标矩形重叠不足 50%"

    # ---- 4. 掩码转多边形 ----
    polygon = loader.mask_to_polygon(mask)
    assert len(polygon) >= 3, f"多边形点数不足: {len(polygon)}"
    print(f"[4] 掩码转多边形: {len(polygon)} 个顶点")

    # 多边形应近似覆盖掩码区域（面积比合理）
    poly_area = cv2.contourArea(np.array(polygon, dtype=np.float32))
    ratio = poly_area / fg_area if fg_area else 0
    print(f"    多边形面积 {poly_area:.0f} / 掩码面积 {fg_area} = {ratio:.2f}")
    assert 0.5 < ratio < 1.3, f"多边形/掩码面积比异常: {ratio:.2f}"

    # ---- 5. 背景点修正（掩码层面 flood-fill 挖除） ----
    # MobileSAM 对负点提示响应弱, 背景点采用挖除所在连通区域的方案
    mask2 = loader.remove_region_at(mask, 380, 70)  # 背景点在干扰物中心
    assert mask2 is not None
    area2 = int(mask2.sum())
    print(f"[5] 背景点挖除: 面积 {area2}（原 {fg_area}）")
    # 干扰物(360,40)-(440,110) 区域应被挖除
    interference = int(mask2[40:110, 360:440].sum())
    print(f"    干扰物区域内掩码像素: {interference}")
    assert interference == 0, "背景点未挖除干扰物区域"
    # 目标大矩形区域应保留
    target_keep = int(mask2[90:230, 120:320].sum())
    assert target_keep > target_rect_area * 0.8, "挖除误伤了目标区域"
    print(f"    目标区域保留: {target_keep} / {target_rect_area}")

    # 背景点在掩码外时不应报错
    mask3 = loader.remove_region_at(mask, 5, 5)  # 背景背景点(不在掩码内)
    assert mask3 is not None and int(mask3.sum()) == fg_area
    print("    掩码外背景点: 无副作用 OK")

    # ---- 6. 空/非法输入容错 ----
    assert loader.predict_mask(image, []) is None, "空点输入应返回 None"
    assert loader.mask_to_polygon(None) == [], "None 掩码应返回空多边形"
    empty = np.zeros((h, w), dtype=np.uint8)
    assert loader.mask_to_polygon(empty) == [], "空掩码应返回空多边形"
    print("[6] 容错测试通过")

    # ---- 7. 可视化输出（供人工查看） ----
    viz = cv2.imread(test_img_path)
    overlay = viz.copy()
    overlay[mask > 0] = (0, 255, 0)
    viz = cv2.addWeighted(viz, 0.6, overlay, 0.4, 0)
    cv2.polylines(viz, [np.array(polygon, dtype=np.int32)],
                  True, (0, 200, 255), 2)
    for (px, py, plabel) in [fg[0] + [1]]:
        color = (0, 255, 0) if plabel == 1 else (0, 0, 255)
        cv2.circle(viz, (px, py), 6, color, -1)
    cv2.circle(viz, (380, 70), 6, (0, 0, 255), -1)  # 背景点(干扰物中心)
    cv2.imwrite("test_data/ai_polygon_viz.png", viz)
    print("[7] 可视化已保存: test_data/ai_polygon_viz.png")

    print("\n=== 全部测试通过 ===")


if __name__ == "__main__":
    main()
