# 将原版 MobileSAM 官方权重转换为 Ultralytics 格式
# 背景: models/mobile_sam.pt 是官方 MobileSAM(state_dict, image_encoder.* 前缀),
#       ultralytics 通用加载器要求 ckpt["model"] 为 nn.Module 实例, 因此无法直接加载。
#       但 ultralytics 的 mobile SAM 架构(TinyViT 配置)与官方完全一致, 可直接 load_state_dict。
# 产物: models/mobile_sam.pt (ultralytics 格式, 可被 YOLO() 加载)
import os
import sys

import torch

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(ROOT, "models")
ORIG = os.path.join(MODELS_DIR, "mobile_sam_original.bak")
OUT = os.path.join(MODELS_DIR, "mobile_sam.pt")

assert os.path.exists(ORIG), f"缺少原版权重备份: {ORIG}"

# 1. 构建 ultralytics mobile SAM 架构
from ultralytics.models.sam.build import build_mobile_sam

model = build_mobile_sam()
model.eval()
print(f"[1] 构建 ultralytics mobile SAM 架构 OK, 参数: {sum(p.numel() for p in model.parameters())/1e6:.1f}M")

# 2. 载入原版 state_dict
sd = torch.load(ORIG, map_location="cpu", weights_only=True)
if isinstance(sd, dict) and "model" in sd and isinstance(sd["model"], dict):
    sd = sd["model"]
print(f"[2] 原版 state_dict keys: {len(sd)}")

result = model.load_state_dict(sd, strict=False)
print(f"[3] 匹配结果: missing={len(result.missing_keys)}, unexpected={len(result.unexpected_keys)}")
if result.missing_keys:
    print("    missing 示例:", result.missing_keys[:8])
if result.unexpected_keys:
    print("    unexpected 示例:", result.unexpected_keys[:8])
if result.missing_keys or result.unexpected_keys:
    print("    !! 存在不匹配, 转换可能不完整, 请检查")

# 3. 按 ultralytics SAM 格式保存
#    注意: SAM 类加载走 build_sam -> _load_checkpoint, 期望 ckpt["model"] 是
#    裸 state_dict(dict) 而非 nn.Module; 且架构由文件名结尾 mobile_sam.pt 决定。
ckpt = {
    "model": model.state_dict(),
    "yaml_file": "mobile_sam.yaml",
    "task": "segment",
}
torch.save(ckpt, OUT)
print(f"[4] 已保存 ultralytics 格式: {OUT} ({os.path.getsize(OUT)/1024/1024:.1f} MB)")

# 4. 验证能被 ultralytics SAM 类加载
from ultralytics import SAM

m = SAM(OUT)
print(f"[5] SAM('{OUT}') 加载成功: {type(m.model).__name__}, task={m.task}")
print("=== 转换完成 ===")
