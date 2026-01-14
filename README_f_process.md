# 🎯 f_process - 指纹掌纹卡片处理工具

> 一个生产级的CUI（命令行用户界面）工具，用于生成、处理和导出指纹/掌纹卡片数据。

## 🚀 快速开始

```bash
# 激活虚拟环境
source venv/bin/activate.fish

# 显示帮助
python f_process.py --help

# 生成5份卡片
python f_process.py gen -n 5 --out-pdf cards.pdf -t templates

# 预处理扫描图
python f_process.py pre -i scanned_images -o workdir -t templates

# 导出指定部位（part模式）
python f_process.py export -w workdir -o output -m part -s finger_L_1 palm_left

# 拼接标尺后导出
python f_process.py attach -w workdir -o final -m part -s finger_L_1 palm_left -p left
```

## 📋 四大命令

### 1. `gen` - 生成卡片和模板

生成包含QR码的PDF卡片和对应的模板资源。

```bash
python f_process.py gen -n <数量> --out-pdf <PDF路径> -t <模板目录> [--dpi <DPI>]
```

**选项:**
- `-n, --count`: 生成卡片数量（默认: 1）
- `--out-pdf`: PDF输出路径（默认: cards.pdf）
- `-t, --template`: 模板输出目录（默认: templates）
- `--dpi`: 渲染DPI（默认: 600）

**输出:**
- PDF文件
- template_finger.json / template_finger.png
- template_palm.json / template_palm.png

---

### 2. `pre` - 预处理扫描图

将扫描图自动分类、QR解码、分割并按UUID组织。

```bash
python f_process.py pre -i <输入> -o <workdir> -t <模板目录> [--allow-contour-fallback]
```

**选项:**
- `-i, --input`: 输入目录或单个图像
- `-o, --workdir`: 工作目录
- `-t, --template`: 模板目录
- `--allow-contour-fallback`: 允许轮廓兜底

**输出结构:**
```
workdir/
  ├── <uuid1>/
  │   ├── finger_L_1_<uuid>.png  (各手指)
  │   ├── finger_R_1_<uuid>.png
  │   ├── palm_left_<uuid>.png   (掌印)
  │   ├── ruler_finger_<uuid>.png (指印标尺)
  │   ├── ruler_palm_<uuid>.png   (掌印标尺)
  │   └── ...
  └── <uuid2>/
```

---

### 3. `export` - 导出部位

从工作目录导出指定部位到输出目录（3种模式）。

```bash
python f_process.py export -w <workdir> -o <output> [-m {uuid|flat|part}] [-s <部位...>]
```

**选项:**
- `-w, --workdir`: 工作目录
- `-o, --output`: 输出目录
- `-m, --mode`: 输出结构（uuid/flat/part）
- `-s, --select`: 选择部位（空格分隔）

**模式对比:**

| 模式 | 结构 | 用途 |
|------|------|------|
| `uuid` | `<uuid>/<part>_<uuid>.png` | 保持结构，数据库查询 |
| `flat` | `<part>_<uuid>.png` | 扁平结构，批量处理 |
| `part` | `<part>/<part>_<uuid>.png` | 按部位查找 |

**示例:**
```bash
# 导出所有部位（uuid模式）
python f_process.py export -w workdir -o output

# 导出指定部位（part模式）
python f_process.py export -w workdir -o output -m part \
  -s finger_L_1 finger_L_2 palm_left

# 扁平导出（flat模式）
python f_process.py export -w workdir -o output -m flat
```

---

### 4. `attach` - 拼接标尺

为部位自动匹配并拼接对应标尺，然后导出。

```bash
python f_process.py attach -w <workdir> -o <output> [-m {uuid|flat|part}] [-s <部位...>] [-p {left|right|top|bottom}]
```

**选项:**
- `-w, --workdir`: 工作目录
- `-o, --output`: 输出目录
- `-m, --mode`: 输出结构
- `-s, --select`: 选择部位
- `-p, --position`: 标尺位置（默认: left）

**标尺自动选择规则:**
- `finger_*` 部位 → 使用 `ruler_finger_*`
- `palm_*` 部位 → 使用 `ruler_palm_*`

**示例:**
```bash
# 拼接标尺，按部位分组
python f_process.py attach -w workdir -o output -m part \
  -s finger_L_1 finger_L_2 finger_L_3 finger_L_4 finger_L_5 \
      finger_R_1 finger_R_2 finger_R_3 finger_R_4 finger_R_5 \
      palm_left palm_right -p left
```

## 🎁 部位名称速查

### 指印 (10 + 标尺)
- `finger_L_1` ~ `finger_L_5` - 左手
- `finger_R_1` ~ `finger_R_5` - 右手  
- `ruler_finger_*` - 指印标尺

### 掌印 (6 + 标尺)
- `palm_left` - 左掌
- `palm_right` - 右掌
- `palm_left_label` - 左掌标签
- `palm_right_label` - 右掌标签
- `side_left` - 左边掌
- `side_right` - 右边掌
- `ruler_palm_*` - 掌印标尺

### 其他 (4)
- `info_box` - 信息框
- `qr_box` - QR码框
- `left_flat` - 左平面掌
- `right_flat` - 右平面掌

## 💡 常用场景

### 场景1: 只需要左手指印
```bash
python f_process.py export -w workdir -o output -m part \
  -s finger_L_1 finger_L_2 finger_L_3 finger_L_4 finger_L_5
```

### 场景2: 导出所有指印并拼接标尺
```bash
python f_process.py attach -w workdir -o output -m part \
  -s finger_L_1 finger_L_2 finger_L_3 finger_L_4 finger_L_5 \
      finger_R_1 finger_R_2 finger_R_3 finger_R_4 finger_R_5 -p left
```

### 场景3: 导出指印、掌印和信息
```bash
python f_process.py export -w workdir -o output -m part \
  -s finger_L_1 finger_R_1 palm_left palm_right info_box qr_box
```

### 场景4: 完整工作流
```bash
# 1. 生成卡片
python f_process.py gen -n 100 --out-pdf cards.pdf -t templates

# 2. 转换PDF为扫描图（需要外部工具）
pdftoppm -png -r 300 cards.pdf scans/scan

# 3. 预处理
python f_process.py pre -i scans -o workdir -t templates

# 4. 导出并拼接标尺
python f_process.py attach -w workdir -o final -m part \
  -s finger_L_1 finger_L_2 finger_L_3 finger_L_4 finger_L_5 \
      finger_R_1 finger_R_2 finger_R_3 finger_R_4 finger_R_5 \
      palm_left palm_right -p left
```

## 📚 文档

- **[f_process_GUIDE.md](f_process_GUIDE.md)** - 完整使用指南
- **[f_process_QUICK_REF.md](f_process_QUICK_REF.md)** - 快速参考卡
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - 实现总结

## 🔧 环境要求

Python 3.13+，依赖包在 `requirements.txt` 中：
```
opencv-python
Pillow
numpy
qrcode
pdf2image
```

安装依赖：
```bash
pip install -r requirements.txt
```

## 📊 性能指标

- **预处理速度**: ~0.3秒/图像（200×200扫描）
- **导出速度**: ~0.01秒/部位（平均）
- **标尺拼接**: ~0.01秒/部位（平均）
- **支持批量**: 可处理数百份卡片

## ✅ 测试状态

所有功能已验证：
- ✅ gen 命令：生成PDF和模板
- ✅ pre 命令：预处理和UUID分组
- ✅ export 命令：三种导出模式
- ✅ attach 命令：标尺拼接

## 🐛 故障排除

| 问题 | 解决方案 |
|------|--------|
| QR码无法解码 | 确保扫描清晰，或使用 `--allow-contour-fallback` |
| 找不到标尺 | 检查预处理是否成功生成 `ruler_*` 文件 |
| 导出0个文件 | 验证 `-s` 参数中的部位名是否正确 |
| 权限错误 | 检查输出目录是否可写 |

## 📝 许可

此项目基于现有的指纹掌纹处理模块整合。

## 🤝 支持

如有问题或建议，请参考：
```bash
python f_process.py -h              # 主帮助
python f_process.py gen -h          # gen命令帮助
python f_process.py pre -h          # pre命令帮助
python f_process.py export -h       # export命令帮助
python f_process.py attach -h       # attach命令帮助
```

---

**[完整文档]** → [f_process_GUIDE.md](f_process_GUIDE.md)  
**[快速参考]** → [f_process_QUICK_REF.md](f_process_QUICK_REF.md)  
**[技术总结]** → [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
