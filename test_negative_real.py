# 真实粘连场景: 目标与干扰物可视觉区分但紧贴, 验证模型负点
# 运行: D:/anaconda/envs/yoloe/python.exe test_negative_real.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from modules.sam_loader import SAMLoader  # noqa: E402


def wrong(m):
    return int((m > 0.5)[90:230, 300:380].sum())  # 干扰物区域


def main():
    # 场景1: 目标亮色 + 紧贴暗色干扰(可区分, 有边界线)
    img = np.full((320, 480, 3), 25, dtype=np.uint8)
    cv2.rectangle(img, (120, 90), (300, 230), (200, 180, 100), -1)   # 目标
    cv2.rectangle(img, (300, 90), (380, 230), (120, 100, 60), -1)    # 干扰(暗色紧贴)
    # 场景2: 目标 + 有1px缝隙的干扰
    img2 = np.full((320, 480, 3), 25, dtype=np.uint8)
    cv2.rectangle(img2, (120, 90), (300, 230), (200, 180, 100), -1)
    cv2.rectangle(img2, (302, 90), (382, 230), (200, 180, 100), -1)  # 2px 缝隙

    fg = [[210, 160]]
    bg = [[340, 160]]

    for name, image in [("紧贴可区分", img), ("2px缝隙", img2)]:
        print(f"\n=== {name} ===")
        for path in [r"models\sam2_t.pt", r"models\sam2.1_t.pt", r"models\mobile_sam.pt"]:
            loader = SAMLoader()
            ok, msg = loader.load_model(path)
            assert ok, msg
            m0 = loader.predict_mask(image, fg)
            m1 = loader.predict_mask(image, fg, bg)
            w0, w1 = wrong(m0), wrong(m1)
            print(f"  {os.path.basename(path):<22}: 仅正 a={int(m0.sum())} 误={w0} | 加负点 a={int(m1.sum())} 误={w1}")


if __name__ == "__main__":
    main()
