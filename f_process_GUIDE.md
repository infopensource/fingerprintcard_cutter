# f_process 指纹掌纹处理CLI使用指南

## 概述

`f_process` 是一个完整的指纹/掌纹卡片处理命令行工具，集成了以下功能：
- **gen**: 生成多页PDF + 模板资源
- **pre**: 预处理扫描图并分割到工作目录（按UUID分组）
- **export**: 从工作目录批量导出（3种目录结构）
- **attach**: 导出时批量拼接标尺

## 工作流

### 1. 生成卡片和模板 (gen)

```bash
# 生成5份卡片（每份2页），输出PDF和模板
python f_process.py gen -n 5 --out-pdf ./cards.pdf -t ./templates --dpi 600
```

参数说明：
- `-n, --count`: 生成卡片数量（每份2页：指印页+掌印页）
- `--out-pdf`: PDF输出路径（默认: cards.pdf）
- `-t, --template`: 模板输出目录（默认: templates）
- `--dpi`: 渲染DPI（默认: 600）

输出结构：
```
cards.pdf                      # 生成的PDF文件
templates/
  ├── template_finger.json     # 指印模板
  ├── template_finger.png      # 指印模板图
  ├── template_palm.json       # 掌印模板
  └── template_palm.png        # 掌印模板图
```

### 2. 预处理扫描图 (pre)

```bash
# 预处理扫描图到工作目录（按UUID分组）
python f_process.py pre -i ./scanned_images -o ./workdir -t ./templates --allow-contour-fallback
```

参数说明：
- `-i, --input`: 输入目录或单个图像文件
- `-o, --workdir`: 工作目录（输出按UUID的子目录）
- `-t, --template`: 模板目录（含template_finger.json等）
- `--allow-contour-fallback`: 允许角块缺失时使用外轮廓兜底

输出结构：
```
workdir/
  ├── <uuid1>/
  │   ├── finger_L_1_<uuid1>.png
  │   ├── finger_L_2_<uuid1>.png
  │   ├── palm_left_<uuid1>.png
  │   ├── ruler_finger_<uuid1>.png
  │   ├── ruler_palm_<uuid1>.png
  │   └── ...
  └── <uuid2>/
      ├── finger_L_1_<uuid2>.png
      └── ...
```

### 3. 导出redirect (export)

```bash
# 按uuid输出（默认）
python f_process.py export -w ./workdir -o ./redirect_uuid

# Flat扁平输出（只导出指定部位）
python f_process.py export -w ./workdir -o ./redirect_flat -m flat -s finger_L_3 palm_left

# 按部位分组输出
python f_process.py export -w ./workdir -o ./redirect_part -m part
```

参数说明：
- `-w, --workdir`: 工作目录
- `-o, --output`: 输出目录
- `-s, --select`: 仅导出指定部位（空=导出全部）
  - 支持空格分隔，例如：`finger_L_1 finger_L_2 palm_left qr info`
- `-m, --mode`: 输出目录结构
  - `uuid` (默认): `output/<uuid>/<part>_<uuid>.png`
  - `flat`: `output/<part>_<uuid>.png`
  - `part`: `output/<part>/<part>_<uuid>.png`

#### Mode详解

**mode=uuid（默认）**
```
output/
  ├── <uuid1>/
  │   ├── finger_L_1_<uuid1>.png
  │   ├── finger_L_2_<uuid1>.png
  │   └── ...
  └── <uuid2>/
      └── ...
```

**mode=flat**
```
output/
  ├── finger_L_1_<uuid1>.png
  ├── finger_L_1_<uuid2>.png
  ├── palm_left_<uuid1>.png
  └── ...
```

**mode=part**
```
output/
  ├── finger_L_1/
  │   ├── finger_L_1_<uuid1>.png
  │   └── finger_L_1_<uuid2>.png
  ├── finger_L_2/
  │   └── ...
  └── palm_left/
      └── ...
```

### 4. 拼接标尺后导出 (attach)

```bash
# 自动选指印/掌印标尺并拼接
python f_process.py attach -w ./workdir -o ./redirect_with_ruler -m part -s finger_L_1 palm_left -p left
```

参数说明：
- `-w, --workdir`: 工作目录
- `-o, --output`: 输出目录
- `-s, --select`: 仅处理指定部位（空=处理全部可拼接部位）
- `-m, --mode`: 输出目录结构（同export，默认: uuid）
- `-p, --position`: 标尺位置
  - `left` (默认): 标尺在左边
  - `right`: 标尺在右边
  - `top`: 标尺在上边
  - `bottom`: 标尺在下边

自动标尺选择规则：
- 部位名以 `finger_` 开头 → 使用 `ruler_finger_*`
- 部位名以 `palm_` 开头 → 使用 `ruler_palm_*`

## 完整工作流示例

```bash
# 1. 生成10份卡片
python f_process.py gen -n 10 --out-pdf ./my_cards.pdf -t ./my_templates

# 2. 将PDF转为扫描图像（使用外部工具，如：pdftoppm）
pdftoppm -png -r 300 ./my_cards.pdf ./scans/scan

# 3. 预处理扫描图到工作目录
python f_process.py pre -i ./scans -o ./workdir -t ./my_templates

# 4. 导出指定部位（flat模式）
python f_process.py export -w ./workdir -o ./export_finger \
  -m flat -s finger_L_1 finger_L_2 finger_L_3 finger_L_4 finger_L_5

# 5. 拼接标尺后导出（part模式）
python f_process.py attach -w ./workdir -o ./export_with_ruler \
  -m part -s finger_L_1 finger_L_2 palm_left palm_right -p left

# 6. 导出全部部位（包括palm信息和QR码）
python f_process.py export -w ./workdir -o ./export_all -m part
```

## 支持的部位名称

### 指印 (Fingerprints)
- `finger_L_1`, `finger_L_2`, `finger_L_3`, `finger_L_4`, `finger_L_5` - 左手
- `finger_R_1`, `finger_R_2`, `finger_R_3`, `finger_R_4`, `finger_R_5` - 右手
- `ruler_finger_*` - 指印标尺

### 掌印 (Palmprints)
- `palm_left` - 左掌
- `palm_right` - 右掌
- `palm_left_label` - 左掌标签
- `palm_right_label` - 右掌标签
- `ruler_palm_*` - 掌印标尺

### 其他
- `info_box` - 信息框
- `qr_box` - QR码框
- `left_flat`, `right_flat` - 平面掌印
- `side_left`, `side_right` - 侧面掌印

## 常见用法

### 只导出某只手的所有指印
```bash
python f_process.py export -w ./workdir -o ./output \
  -m part -s finger_L_1 finger_L_2 finger_L_3 finger_L_4 finger_L_5
```

### 拼接标尺并导出所有指印
```bash
python f_process.py attach -w ./workdir -o ./output \
  -m part -s finger_L_1 finger_L_2 finger_L_3 finger_L_4 finger_L_5 \
          finger_R_1 finger_R_2 finger_R_3 finger_R_4 finger_R_5 -p right
```

### 导出指印、掌印和信息
```bash
python f_process.py export -w ./workdir -o ./output -m part \
  -s finger_L_1 finger_R_1 palm_left palm_right info_box qr_box
```

## 环境要求

确保在虚拟环境中安装了依赖：
```bash
pip install -r requirements.txt
```

包含的库：
- opencv-python - 图像处理
- Pillow - 图像I/O
- numpy - 数值计算
- qrcode - QR码编码
- pdf2image - PDF转换

## 故障排除

### 预处理失败：QR码无法解码
- 确保扫描图像清晰且QR码完整
- 尝试使用 `--allow-contour-fallback` 选项

### 找不到标尺
- 检查workdir中是否存在 `ruler_finger_*` 或 `ruler_palm_*` 文件
- 确保预处理成功生成了标尺文件

### 导出文件不完整
- 检查-s参数的部位名是否正确
- 使用 `export` 命令验证workdir中存在这些部位
