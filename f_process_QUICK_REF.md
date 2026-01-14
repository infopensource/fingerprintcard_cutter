# f_process 快速参考

## 基本语法

```bash
python f_process.py <command> [options]
```

## 四大命令

### 1️⃣ gen - 生成卡片和模板

```bash
python f_process.py gen -n <数量> --out-pdf <PDF路径> -t <模板目录> [--dpi <DPI>]
```

| 参数 | 默认值 | 说明 |
|-----|-------|------|
| `-n` | 1 | 生成卡片数量 |
| `--out-pdf` | cards.pdf | 输出PDF路径 |
| `-t` | templates | 模板输出目录 |
| `--dpi` | 600 | 渲染DPI |

### 2️⃣ pre - 预处理扫描图

```bash
python f_process.py pre -i <输入> -o <工作目录> -t <模板目录> [--allow-contour-fallback]
```

| 参数 | 说明 |
|-----|------|
| `-i` | 输入目录或单个图像 |
| `-o` | 工作目录（按UUID分组） |
| `-t` | 模板目录 |
| `--allow-contour-fallback` | 允许轮廓兜底 |

### 3️⃣ export - 导出部位

```bash
python f_process.py export -w <工作目录> -o <输出> [-m {uuid,flat,part}] [-s <部位列表>]
```

| 参数 | 默认值 | 说明 |
|-----|-------|------|
| `-w` | - | 工作目录 |
| `-o` | - | 输出目录 |
| `-m` | uuid | 目录模式：uuid/flat/part |
| `-s` | 全部 | 要导出的部位（空格分隔） |

**模式对比**
- `uuid`: `<uuid>/<part>_<uuid>.png`
- `flat`: `<part>_<uuid>.png`
- `part`: `<part>/<part>_<uuid>.png`

### 4️⃣ attach - 拼接标尺

```bash
python f_process.py attach -w <工作目录> -o <输出> [-m {uuid,flat,part}] [-s <部位列表>] [-p {left,right,top,bottom}]
```

| 参数 | 默认值 | 说明 |
|-----|-------|------|
| `-w` | - | 工作目录 |
| `-o` | - | 输出目录 |
| `-m` | uuid | 目录模式 |
| `-s` | 全部 | 要处理的部位 |
| `-p` | left | 标尺位置 |

## 部位代码

### 指印 (Fingerprints)
- `finger_L_1` ~ `finger_L_5` - 左手5根手指
- `finger_R_1` ~ `finger_R_5` - 右手5根手指
- `ruler_finger_*` - 指印标尺

### 掌印 (Palmprints)
- `palm_left` / `palm_right` - 左/右掌
- `palm_left_label` / `palm_right_label` - 掌印标签
- `ruler_palm_*` - 掌印标尺

### 其他
- `info_box` - 信息框
- `qr_box` - QR码框

## 常用场景

### 导出所有左手指印
```bash
python f_process.py export -w ./workdir -o ./output -m part \
  -s finger_L_1 finger_L_2 finger_L_3 finger_L_4 finger_L_5
```

### 导出指印并拼接标尺（左对齐）
```bash
python f_process.py attach -w ./workdir -o ./output -m part \
  -s finger_L_1 finger_L_2 finger_L_3 finger_L_4 finger_L_5 \
      finger_R_1 finger_R_2 finger_R_3 finger_R_4 finger_R_5 -p left
```

### 导出指印和掌印（按部位分组）
```bash
python f_process.py export -w ./workdir -o ./output -m part \
  -s finger_L_1 finger_R_1 palm_left palm_right
```

### Flat模式导出特定部位
```bash
python f_process.py export -w ./workdir -o ./output -m flat \
  -s finger_L_1 finger_L_2 palm_left
```

## 工作流例子

```bash
# 第1步：生成卡片
python f_process.py gen -n 50 --out-pdf cards.pdf -t templates

# 第2步：扫描PDF生成图像（使用系统工具）
pdftoppm -png -r 300 cards.pdf scans/scan

# 第3步：预处理
python f_process.py pre -i scans -o workdir -t templates

# 第4步：导出并拼接标尺
python f_process.py attach -w workdir -o final_output -m part \
  -s finger_L_1 finger_L_2 finger_L_3 finger_L_4 finger_L_5 \
      finger_R_1 finger_R_2 finger_R_3 finger_R_4 finger_R_5 \
      palm_left palm_right -p left
```

## 错误排查

| 问题 | 解决方案 |
|------|--------|
| QR码无法解码 | 扫描清晰度不足或使用 `--allow-contour-fallback` |
| 找不到标尺 | 检查预处理是否成功生成 ruler_* 文件 |
| 导出0个文件 | 检查 -s 参数中的部位名是否正确 |
| 权限错误 | 确保输出目录可写 |

## 获取帮助

```bash
# 主帮助
python f_process.py -h

# 子命令帮助
python f_process.py gen -h
python f_process.py pre -h
python f_process.py export -h
python f_process.py attach -h
```
