# YOLOE + SAM 自动标注系统

基于 [Ultralytics YOLOE](https://docs.ultralytics.com/) 与 [SAM 2](https://docs.ultralytics.com/models/sam-2/) 的桌面图像标注工具（PyQt6）。既可以用 YOLOE 做全自动预测和视觉提示批量标注，也可以用 SAM 做点提示的交互式多边形标注，最终导出 YOLO 检测 / 分割 / 姿态标签。

## 功能特性

**自动标注**
- 加载 YOLOE 模型后一键预测检测框、分割掩码或关键点
- 视觉提示（Visual Prompt）：在图上框选目标作为提示，YOLOE 据此在整张图中查找同类目标；缓存 VPE 后可对文件夹内所有图像做「同类标签自动标注」

**AI 交互式分割**
- 基于 SAM / SAM 2 / MobileSAM 的 AI 多边形：左键加前景点、右键加背景点，实时生成分割预览
- 掩码自动简化为多边形（Douglas-Peucker + 顶点数上限），确认时可直接转成 Seg 标注并自动保存
- 支持 SAM 2、SAM 2.1 与 MobileSAM 权重；特征缓存后加点只跑掩码解码器，交互跟手

**批量推理**
- 用任意 YOLO 检测 / 分割 / 姿态模型对整个文件夹批量推理，直接写出同名 YOLO 标签
- 可调置信度与 IoU 阈值，覆盖已有标签前会确认，完成后自动更新 `classes.txt`

**编辑与导出**
- 手动绘制、移动、缩放、方向键微调边界框；删除 / 清空 / 修改类别与置信度
- 检测框、Pose 骨架（按类别自定义放射状连接）、Seg 多边形三类标注同屏显示
- 单张 / 批量导出 YOLO 检测、Pose、Seg 格式

**数据集与格式**
- 按 train / val / test 比例划分图像与标签，无标签图像归入 `blank`，自动生成 YOLO 目录结构
- Labelme JSON ↔ YOLO-seg TXT、YOLO 检测 TXT ↔ 通用 JSON 格式互转

## 环境要求

- Python 3.8+
- PyTorch（有 NVIDIA GPU 时建议安装对应 CUDA 版本）
- ultralytics（需包含 YOLOE / SAM 2 支持）

## 安装

```bash
pip install -r requirements.txt
```

`requirements.txt` 包含：PyQt6、numpy、opencv-python、pillow、torch、torchvision、ultralytics、pyyaml。

## 模型权重

模型权重体积较大，**不包含在仓库中**（`models/`、`*.pt` 已在 `.gitignore` 中忽略），需自行准备：

| 用途 | 放置位置 | 说明 |
| --- | --- | --- |
| YOLOE 自动标注 / 视觉提示 | 任意位置 | 在界面「模型设置」中选择 YOLOE 权重（`.pt`），可参考 [YOLOE 文档](https://docs.ultralytics.com/models/yoloe/) |
| 批量模型标注 | 任意位置 | 右侧「批量模型标注」中选择 YOLO 检测 / 分割 / 姿态权重 |
| AI 多边形（SAM） | `models/sam2_t.pt` | `Config.AI_POLYGON_CONFIG['default_weights_path']` 的默认路径 |

SAM 权重说明：

- 推荐 `sam2_t.pt`（约 75 MB），官方正/负点提示均有效。
- 官方命名（如 `sam2_hiera_tiny.pt`、`sam2.1_hiera_tiny.pt`）会被自动复制为 ultralytics 标准名后加载。
- `sam2.1_t.pt` 与 MobileSAM 在 CPU 上更快，但**负点响应较弱**；程序会自动回退为掩码 flood-fill 挖除背景点。
- 使用原版 MobileSAM 官方权重时，先运行 `python convert_sam.py` 转换为 ultralytics 格式（需要 `models/mobile_sam_original.bak`）。

## 快速开始

```bash
python app.py
```

1. 在左侧「模型设置」选择 YOLOE 权重并点击「加载模型」。
2. 通过文件树或「文件 → 打开文件夹」打开数据目录，程序会自动加载同名 `.txt` 标签。
3. 点击「自动标注」或「AI 多边形」开始标注，`Ctrl+S` 保存。

## 使用说明

### 1. 自动标注

加载模型后点击「自动标注」对当前图像预测；预测结果按模型任务写为检测框、分割掩码或关键点。加载成功后模型类别会写入当前文件夹的 `classes.txt`。

### 2. 视觉提示标注（同类批量）

1. 点击「开始绘制视觉提示」，在图像上框选目标并输入类别标签；
2. 点击「停止绘制」缓存 VPE；
3. 点击「同类标签自动标注」，对文件夹内所有图像批量标注同类目标。

### 3. AI 多边形（交互式 SAM 分割）

点击工具栏「AI 多边形」或按 `Ctrl+P` 进入（首次使用会自动加载 `models/sam2_t.pt`）：

| 操作 | 作用 |
| --- | --- |
| 左键单击 | 添加前景点（绿色） |
| 右键单击 | 添加背景点（红色），排除误分割区域 |
| `Backspace` | 撤销上一个提示点 |
| `Enter` | 确认预览，选择类别并生成 Seg 标注（自动保存） |
| `Esc` | 退出 AI 多边形模式 |

确认后会清空提示点但保持模式，可连续标注多个目标。

### 4. 批量模型标注

在右侧「批量模型标注」面板选择 YOLO 权重并「加载模型」，设置置信度 / IoU 后点击「批量标注」：

- 对当前文件夹内所有图像推理，写出同名 `.txt`；
- 检测 / 分割 / 姿态模型会分别输出对应的 YOLO 行格式；
- 若已有非空标签，会先提示覆盖；
- 完成后把模型类别写入当前文件夹的 `classes.txt`。

### 5. 手动编辑

按 `W` 切换手动标注模式，在图像上拖拽绘制新框；选中后可拖拽移动 / 调整手柄，方向键微调 1 像素，`Delete` 删除选中标注。

### 6. 保存与导出

- `Ctrl+S` 保存标注（默认写在图像同目录同名 `.txt`）；
- `Ctrl+E` 导出当前标注到指定目录；
- 「文件 → 批量导出」（`Ctrl+Shift+E`）批量导出当前文件夹。

### 7. 组织数据集

设置输出目录与 train / val / test 比例（三者之和为 1），点击「组织数据集」，生成 `images|labels/{train,val,test}` 结构；无标签图像归入 `blank`。

### 8. 格式转换

「工具 → YOLO 格式转换 (TXT ↔ JSON)」支持 Labelme JSON ↔ YOLO-seg TXT、YOLO 检测 TXT ↔ 通用 JSON。

## 快捷键

| 快捷键 | 功能 |
| --- | --- |
| `A` / `D` | 上一张 / 下一张图像 |
| `Space` | 保存当前图像并跳到下一张 |
| `Ctrl+O` / `Ctrl+Shift+O` | 打开图像 / 打开文件夹 |
| `Ctrl+S` / `Ctrl+E` | 保存标注 / 导出标注 |
| `Ctrl+Shift+E` | 批量导出 |
| `Ctrl+P` | 进入 / 退出 AI 多边形 |
| `W` | 切换手动标注模式 |
| `Delete` | 删除选中标注 |
| `←` `→` `↑` `↓` | 微调选中标注（1 像素） |
| 鼠标滚轮 | 缩放 |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` | 放大 / 缩小 / 重置缩放 |
| `Ctrl+Q` | 退出 |

## 配置说明

所有可调参数集中在 [`config.py`](config.py) 的 `Config` 类：

- `MODEL_CONFIG`：YOLOE 权重路径、置信度阈值、IoU 阈值、推理设备
- `AI_POLYGON_CONFIG`：SAM 默认权重路径、提示点颜色、多边形简化容差、最大顶点数、最小面积等
- `ANNOTATION_CONFIG`：框 / 文本 / 关键点 / 骨架 / 分割的颜色与线宽
- `POSE_CONFIG`：关键点名称、COCO 骨架连接、按类别的放射状连接规则
- `GUI_CONFIG`：窗口标题、尺寸、缩放范围
- `EXPORT_CONFIG`：导出目录、是否导出置信度

## 项目结构

```
自动标注系统/
├── app.py                      # 主程序（主窗口、事件、批量标注、组织数据集）
├── config.py                   # 全局配置
├── requirements.txt            # 依赖
├── auto_label.spec             # PyInstaller 打包配置
├── convert_sam.py              # 原版 MobileSAM 权重转 ultralytics 格式
├── modules/
│   ├── model_loader.py         # YOLOE 模型加载与预测（含视觉提示）
│   ├── sam_loader.py           # SAM 模型加载、点提示分割、掩码转多边形
│   ├── ai_polygon_editor.py    # AI 多边形交互状态机
│   ├── batch_labeler.py        # YOLO 模型批量推理写标签
│   ├── label_engine.py         # 自动标注、视觉提示批量标注、标签加载
│   ├── annotation_display.py   # 标注图形显示（框 / 骨架 / 分割）
│   ├── manual_editor.py        # 手动绘制 / 移动 / 缩放
│   ├── label_exporter.py       # YOLO 标签导出与解析
│   ├── image_browser.py        # 图像浏览与视图控制
│   ├── class_manager.py        # 类别管理（classes.txt）
│   ├── dataset_organizer.py    # 数据集划分与拷贝
│   ├── format_converter.py     # Labelme ↔ YOLO 格式转换
│   ├── ui_builder.py           # UI 面板 / 菜单 / 工具栏
│   └── styles.py               # 深色主题样式
└── test_*.py / *_test_*.py     # 自测脚本（Pose 显示、AI 多边形、负点等）
```

## 注意事项

- **类别 ID 是位置式的**：`classes.txt` 每行一个类别名，类别 ID 即行号。添加 / 重命名类别会追加或原位替换（不重排），但**删除中间类别会使后续类别 ID 前移**，已导出的标签含义可能变化，操作前请确认顺序。
- **标签文件默认与图像同目录同名**（`xxx.jpg` ↔ `xxx.txt`）；「保存图像到文件夹」只复制图像，不复制标签。
- 单个标签文件允许混合检测 / Pose / Seg 行，程序按行解析。
- 视觉提示同类批量标注需先完成一次带视觉提示的自动标注（成功缓存 VPE）后才能使用。
- AI 多边形确认后会调用自动保存，直接写入当前图像的标签文件。
- 无 GPU 时 SAM / YOLOE 推理会明显变慢，可在 `config.py` 中把设备改为 `cpu`。

## 许可证

[MIT](LICENSE)
