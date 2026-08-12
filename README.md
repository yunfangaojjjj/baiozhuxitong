# YOLOE 自动标注系统

基于 [Ultralytics YOLOE](https://docs.ultralytics.com/) 的图像自动标注桌面工具（PyQt6 界面）。支持视觉提示（Visual Prompt）批量标注、检测 / Pose / Seg 三种标注格式的显示与导出、数据集自动划分以及 Labelme JSON ↔ YOLO 格式转换。

## 功能特性

- **自动标注**：加载 YOLOE 模型后对图像自动预测检测框 / 分割掩码 / 关键点
- **视觉提示标注**：在图像上框选目标作为提示，YOLOE 据此在整张图上查找同类目标；缓存 VPE 后可对文件夹中所有图像做「同类批量标注」
- **手动编辑**：绘制、移动、缩放、微调边界框；删除 / 清空 / 修改类别与置信度
- **三类标注显示**：检测框、Pose 关键点骨架（按类别自定义放射状连接）、Seg 分割多边形
- **标签导出**：YOLO 检测 / Pose / Seg 格式，单张或批量导出
- **数据集组织**：按 train / val / test 比例划分图像与标签，无标签图像归入 `blank`，自动生成 YOLO 目录结构
- **格式转换**：Labelme JSON ↔ YOLO-seg TXT、YOLO 检测 TXT ↔ 通用 JSON

## 环境要求

- Python 3.8+
- PyTorch（建议 CUDA 版本）
- ultralytics（含 YOLOE 支持）

## 安装

```bash
pip install -r requirements.txt
```

`requirements.txt` 内容：

```
PyQt6
numpy
opencv-python
pillow
torch
torchvision
ultralytics
pyyaml
```

## 使用说明

1. **启动程序**

   ```bash
   python app.py
   ```

2. **加载模型**：左侧「模型设置」中浏览并选择 YOLOE 权重文件（`.pt`），点击「加载模型」。加载成功后模型类别会写入当前文件夹的 `classes.txt`。

3. **打开图像 / 文件夹**：通过左侧文件树或菜单「打开文件夹」打开数据目录，程序会自动加载每张图对应的同名 `.txt` 标签文件。

4. **自动标注**：点击「自动标注」或按 `L` 对当前图像执行自动标注。

5. **视觉提示标注（同类批量）**：
   - 点击「开始绘制视觉提示」，在图像上框选目标并输入类别标签；
   - 点击「停止绘制」缓存 VPE；
   - 点击「同类标签自动标注」，对文件夹中所有图像批量标注同类目标。

6. **手动标注**：按 `W` 切换标注模式，在图像上拖拽绘制新框；选中后可移动 / 拖拽手柄调整大小；方向键微调；`Delete` 删除。

7. **保存 / 导出**：`Ctrl+S` 保存标注（标签文件写在图像同目录），`Ctrl+E` 导出到指定目录，菜单支持批量导出。

8. **组织数据集**：设置输出目录与 train / val / test 比例（和须为 1），点击「组织数据集」，生成 `datasets/bvn/images|labels/{train,val,test}` 结构。

9. **格式转换**：菜单「工具 → YOLO 格式转换」，支持 Labelme JSON ↔ YOLO-seg TXT、检测 TXT ↔ 通用 JSON。

### 快捷键

| 快捷键 | 功能 |
| --- | --- |
| `A` / `D` | 上一张 / 下一张图像 |
| `Space` | 保存当前图像并跳到下一张 |
| `Ctrl+S` | 保存标注 |
| `W` | 切换手动标注模式 |
| `Delete` | 删除选中标注 |
| `Ctrl+滚轮` / `Ctrl+0` | 缩放 / 重置缩放 |

## 配置说明

所有可调参数集中在 [`config.py`](config.py) 的 `Config` 类中：

- `MODEL_CONFIG`：模型权重路径、置信度阈值、IoU 阈值、推理设备
- `ANNOTATION_CONFIG`：框 / 文本 / 关键点 / 骨架 / 分割的颜色与线宽
- `POSE_CONFIG`：关键点名称、COCO 骨架连接、按类别的放射状连接规则
- `GUI_CONFIG`：窗口标题、尺寸、缩放范围
- `EXPORT_CONFIG`：导出目录、是否导出置信度

## 项目结构

```
自动标注系统/
├── app.py                     # 主程序（主窗口、事件、组织数据集）
├── config.py                  # 全局配置
├── requirements.txt           # 依赖
├── auto_label.spec            # PyInstaller 打包配置
├── modules/
│   ├── model_loader.py        # YOLOE 模型加载与预测（含视觉提示）
│   ├── label_engine.py        # 自动 / 批量标注、标签文件加载
│   ├── annotation_display.py  # 标注图形显示（框 / 骨架 / 分割）
│   ├── manual_editor.py       # 手动绘制 / 移动 / 缩放
│   ├── label_exporter.py      # YOLO 标签导出与解析
│   ├── image_browser.py       # 图像浏览与视图控制
│   ├── class_manager.py       # 类别管理（classes.txt）
│   ├── dataset_organizer.py   # 数据集划分与拷贝
│   ├── format_converter.py    # Labelme ↔ YOLO 格式转换
│   ├── ui_builder.py          # UI 面板 / 菜单 / 工具栏
│   └── styles.py              # 深色主题样式
└── test_pose_display.py       # Pose 显示功能自测脚本
```

## 注意事项

- **类别 ID 是位置式的**：`classes.txt` 中每行一个类别名，类别 ID 即为行号。添加 / 重命名类别时会追加到末尾或原位替换（不会重排），但**删除中间类别会使后续类别 ID 前移**，已导出的标签含义可能变化，操作前请确认类别顺序。
- **标签文件默认与图像同目录同名**（`xxx.jpg` ↔ `xxx.txt`）。「保存图像到文件夹」仅复制图像，不会复制标签，请注意。
- 单个标签文件允许混合检测 / Pose / Seg 行，程序按行解析。
- 视觉提示同类批量标注需先完成至少一次带视觉提示的自动标注（成功缓存 VPE）后方可使用。

## 许可证

[MIT](LICENSE)
