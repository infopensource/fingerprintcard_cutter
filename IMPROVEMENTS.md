# f_process 改进日志

## 改进内容

### 1. 双语支持（中英文）
- ✅ 默认英文帮助
- ✅ 通过 `--lang zh` 切换中文帮助
- ✅ 所有命令和参数都有对应的中英文说明

**使用方法：**
```bash
# 英文帮助（默认）
python f_process.py gen --help

# 中文帮助
python f_process.py --lang zh gen --help
```

### 2. 参数默认值完整说明
所有参数的帮助文本现在包含默认值信息：

**gen 命令：**
- `-n, --count`: Number of cards (default: 1)
- `--out-pdf`: Output path (default: cards.pdf)
- `-t, --template`: Template directory (default: templates)
- `--dpi`: Rendering DPI (default: 600)

**pre 命令：**
- `-i, --input`: 必需参数（输入目录或图像）
- `-o, --workdir`: 必需参数（工作目录）
- `-t, --template`: 必需参数（模板目录）

**export 命令：**
- `-m, --mode`: 导出模式 (default: uuid)
- `-s, --select`: 部位选择 (default: 全部)

**attach 命令：**
- `-m, --mode`: 导出模式 (default: uuid)
- `-p, --position`: 标尺位置 (default: left)

### 3. DPI 选项说明增强
在 `--dpi` 参数的帮助文本中添加了详细说明：

**英文：**
```
Rendering DPI for PDF and template images (default: 600). 
Note: higher DPI improves PDF quality but does not affect 
segmentation quality from scans
```

**中文：**
```
PDF 和模板图像的渲染 DPI（默认: 600）。
注：更高的 DPI 改进 PDF 质量，但不影响扫描分割结果的清晰度
```

## DPI 的实际用途分析

根据代码分析，DPI 的意义如下：

| 方面 | 影响 | 说明 |
|------|------|------|
| PDF 生成 | ✅ 有影响 | 控制 PDF 中的内容清晰度 |
| 模板 PNG | ✅ 有影响 | 影响 template_*.png 的清晰度 |
| QR 码质量 | ✅ 有影响 | 高 DPI 生成更清晰的 QR 码 |
| 坐标精度 | ✅ 有影响 | template_*.json 中的坐标精度 |
| 分割结果 | ❌ 无影响 | 分割清晰度取决于输入扫描图 |
| 处理速度 | ❌ 无影响 | 不影响预处理/导出/拼接速度 |

**结论：** DPI 主要影响「生成的 PDF 卡片质量」，保留此选项的意义是支持不同质量需求（如：快速原型用 200 DPI，最终版本用 600+ DPI）。

## 示例

### 英文帮助示例
```bash
$ python f_process.py gen --help
usage: f_process gen [-h] [-n COUNT] [--out-pdf OUT_PDF] [-t TEMPLATE] [--dpi DPI]

options:
  -h, --help            show this help message and exit
  -n, --count COUNT     Number of cards to generate (default: 1)
  --out-pdf OUT_PDF     Output PDF path (default: cards.pdf)
  -t, --template TEMPLATE
                        Template output directory (default: templates)
  --dpi DPI             Rendering DPI for PDF and template images (default: 600). 
                        Note: higher DPI improves PDF quality but does not affect 
                        segmentation quality from scans
```

### 中文帮助示例
```bash
$ python f_process.py --lang zh gen --help
usage: f_process gen [-h] [-n COUNT] [--out-pdf OUT_PDF] [-t TEMPLATE] [--dpi DPI]

options:
  -h, --help            show this help message and exit
  -n, --count COUNT     生成卡片数量（默认: 1）
  --out-pdf OUT_PDF     输出 PDF 路径（默认: cards.pdf）
  -t, --template TEMPLATE
                        模板输出目录（默认: templates）
  --dpi DPI             PDF 和模板图像的渲染 DPI（默认: 600）。注：更高的 DPI 改进 PDF 质量，
                        但不影响扫描分割结果的清晰度
```

## 切换语言方法

### 方法 1：全局选项（推荐）
```bash
# 切换为中文
python f_process.py --lang zh <command> [options]

# 例如
python f_process.py --lang zh gen -n 5 --out-pdf cards.pdf
python f_process.py --lang zh pre -i scans -o workdir -t templates
```

### 方法 2：查看特定子命令的帮助
```bash
# 英文 (默认)
python f_process.py gen --help
python f_process.py pre --help
python f_process.py export --help
python f_process.py attach --help

# 中文
python f_process.py --lang zh gen --help
python f_process.py --lang zh pre --help
python f_process.py --lang zh export --help
python f_process.py --lang zh attach --help
```

## 向后兼容性

✅ 所有原有功能完全保留，无任何破坏性改变
✅ 默认行为不变（英文、所有默认值保持一致）
✅ 所有之前的命令仍然可以正常运行

## 测试验证

所有改进已验证：
- ✅ 英文帮助显示正确，包含默认值
- ✅ 中文帮助切换正常
- ✅ DPI 说明清晰明确
- ✅ 完整工作流（gen → pre → export → attach）正常运行
- ✅ 代码无错误
