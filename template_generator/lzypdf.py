from reportlab.pdfgen.canvas import Canvas
##from reportlab.lib.pagesizes import letter,A4,landscape
from reportlab.pdfbase import pdfmetrics  
#from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
#from reportlab.lib.colors import pink, black, red, blue, green,white
#from reportlab.lib import fonts
from reportlab.lib.units import mm

#from fontTools.ttLib import TTFont as tool_TTFont
import os

# Get the directory where this script is located
_script_dir = os.path.dirname(os.path.abspath(__file__))

pdfmetrics.registerFont(TTFont('华文宋体', os.path.join(_script_dir, 'fontlib', '华文宋体.ttf')))  
Canvas_tran_x = 0  #画布坐标原点的横坐标，单位mm
Canvas_tran_y = 0
#t_x1=15*mm
#t_y1=18*mm
#t_x2=15*mm
#t_y2=18*mm

t_width=210*mm      #纸宽度，A4纸的标准尺寸(210mmX297mm)
t_length=297*mm         #纸长度，A4纸的标准尺寸(210mmX297mm)
t_left=5*mm        #左边距
t_right=5*mm        #右边距
t_top=16*mm        #顶边距
t_bottom=16*mm     #底边距

t_message_height=36*mm   #信息框的高度
t_finger=50*mm      #手指框高度5cm
t_character=8*mm    #字符高度8mm
t_scale_width=20*mm
_output_dir = os.path.join(_script_dir, 'output')
os.makedirs(_output_dir, exist_ok=True)

c = Canvas(os.path.join(_output_dir, 'lzy.pdf'), pagesize=(210*mm, 297*mm))  #A4纸的标

c.setLineWidth(1)  #设置line划线的宽度
c.setFont('华文宋体',15,leading = None) #设定文字字体和字号
#画最下面两大方框
# 画一个长方形，参数分别是左下角坐标（x, y）和宽度及高度）
c.rect(t_left, t_bottom, (t_width-t_right-t_left-1*mm)/2, t_length-t_top-t_message_height-1*mm-2*t_finger-2*t_character-t_bottom, stroke=1, fill=0)  # stroke=1表示绘制边
c.rect(t_left+(t_width-t_right-t_left-1*mm)/2+1*mm,t_bottom, (t_width-t_right-t_left-1*mm)/2, t_length-t_top-t_message_height-1*mm-2*t_finger-2*t_character-t_bottom,stroke=1, fill=0)  # stroke=1表示绘制边
c.drawString(t_left+15, t_bottom-t_character, "左手平面捺印") #在对应位置，按设定的字体和字号输出汉字
c.drawString(t_left+15+(t_width-t_right-t_left-1*mm)/2+1*mm,t_bottom-t_character, "右手平面捺印") #在对应位置，按设定的字体和字号输出汉字


y_finger_start=t_length-t_top-t_message_height-1*mm-2*t_finger-t_character    #确定手指框开始的纵坐标，以简化公式，横坐标仍为t_left
#画手指框下排五个
# 画一个长方形，参数分别是左下角坐标（x, y）和宽度及高度）
c.rect(t_left, y_finger_start, (t_width-t_left-t_right-5*mm-t_scale_width)/5, t_finger, stroke=1, fill=0)  # stroke=1表示绘制边
c.rect(t_left+1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5, y_finger_start, (t_width-t_left-t_right-5*mm-t_scale_width)/5, t_finger, stroke=1, fill=0)  # stroke=1表示绘制边
c.rect(t_left+2*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start, (t_width-t_left-t_right-5*mm-t_scale_width)/5, t_finger, stroke=1, fill=0)  # stroke=1表示绘制边
c.rect(t_left+3*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start, (t_width-t_left-t_right-5*mm-t_scale_width)/5, t_finger, stroke=1, fill=0)  # stroke=1表示绘制边
c.rect(t_left+4*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start, (t_width-t_left-t_right-5*mm-t_scale_width)/5, t_finger, stroke=1, fill=0)  # stroke=1表示绘制边
c.drawString(t_left+5, y_finger_start-t_character+5, "6.左手拇指") #在对应位置，按设定的字体和字号输出汉字
c.drawString(t_left+5+1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5, y_finger_start-t_character+5, "7.左手食指") #在对应位置，按设定的字体和字号输出汉字
c.drawString(t_left+5+2*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start-t_character+5, "8.左手中指") #在对应位置，按设定的字体和字号输出汉字
c.drawString(t_left+5+3*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start-t_character+5, "9.左手环指") #在对应位置，按设定的字体和字号输出汉字
c.drawString(t_left+5+4*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start-t_character+5, "10.左手小指") #在对应位置，按设定的字体和字号输出汉字

#画手指框上排五个
y_finger_start=t_length-t_top-t_message_height-1*mm-1*t_finger   #重新确定手指框开始的纵坐标，以简化公式，并重新利用下排的代码，横坐标仍为t_left
# 画一个长方形，参数分别是左下角坐标（x, y）和宽度及高度）
#以下代码和下排五个相同
c.rect(t_left, y_finger_start, (t_width-t_left-t_right-5*mm-t_scale_width)/5, t_finger, stroke=1, fill=0)  # stroke=1表示绘制边
c.rect(t_left+1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5, y_finger_start, (t_width-t_left-t_right-5*mm-t_scale_width)/5, t_finger, stroke=1, fill=0)  # stroke=1表示绘制边
c.rect(t_left+2*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start, (t_width-t_left-t_right-5*mm-t_scale_width)/5, t_finger, stroke=1, fill=0)  # stroke=1表示绘制边
c.rect(t_left+3*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start, (t_width-t_left-t_right-5*mm-t_scale_width)/5, t_finger, stroke=1, fill=0)  # stroke=1表示绘制边
c.rect(t_left+4*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start, (t_width-t_left-t_right-5*mm-t_scale_width)/5, t_finger, stroke=1, fill=0)  # stroke=1表示绘制边
c.drawString(t_left+5, y_finger_start-t_character+5, "1.右手拇指") #在对应位置，按设定的字体和字号输出汉字
c.drawString(t_left+5+1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5, y_finger_start-t_character+5, "2.右手食指") #在对应位置，按设定的字体和字号输出汉字
c.drawString(t_left+5+2*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start-t_character+5, "3.右手中指") #在对应位置，按设定的字体和字号输出汉字
c.drawString(t_left+5+3*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start-t_character+5, "4.右手环指") #在对应位置，按设定的字体和字号输出汉字
c.drawString(t_left+5+4*(1*mm+(t_width-t_left-t_right-5*mm-t_scale_width)/5), y_finger_start-t_character+5, "5.右手小指") #在对应位置，按设定的字体和字号输出汉字

#画信息框
y_finger_start=t_length-t_top-t_message_height    #确定信息框开始的纵坐标，以简化公式，横坐标仍为t_left
c.rect(t_left, y_finger_start, (t_width-t_left-t_right-t_message_height-t_scale_width-1*mm), t_message_height, stroke=1, fill=0)  # 画信息框，右边留出边长为t_message_height的正方形空间放二维码

#画标尺粘贴框
offset = 7*mm  #标尺框与信息框之间的间隔
y_finger_start=t_length-t_top-t_message_height-1*mm-2*t_finger-t_character-offset  #标尺底边与下排手指框底边对齐+offset
scale_height=t_message_height+1*mm+2*t_finger+t_character+offset                     #标尺顶边与信息框顶边对齐
c.rect(t_width-t_right+0*mm-t_scale_width, y_finger_start, t_scale_width, scale_height, stroke=1, fill=0)  # 画标尺框，右边留出边长为t_message_height的正方形空间放二维码

# 标尺文字居中显示
scale_center_x = t_width - t_right - t_scale_width/2
scale_center_y = y_finger_start + scale_height/2
line_gap = 2*t_character
start_y = scale_center_y + 3*t_character  # 四行文字，间距为 line_gap
c.drawCentredString(scale_center_x, start_y, "标")
c.drawCentredString(scale_center_x, start_y - line_gap, "尺")
c.drawCentredString(scale_center_x, start_y - 2*line_gap, "粘")
c.drawCentredString(scale_center_x, start_y - 3*line_gap, "贴")

##        shupai(string_txt3,45,t_x1-30,t_y1+170,15,c) #奇数页竖排页码页眉到左边


c.showPage()
#另一页
# --------------- 第2页独立参数设置 ---------------
# 为避免与第1页参数冲突，使用 p2_ 前缀定义第2页专用参数
p2_top = 16 * mm
p2_bottom = 16 * mm
p2_left = 5 * mm
p2_right = 5 * mm
p2_scale_height = 20 * mm      # 顶部标尺粘贴区高度
p2_side_height = 30 * mm       # 侧掌区高度
p2_gap_small = 2 * mm          # 各区域间的行间距（紧凑）
p2_char_width = t_character    # 使用之前定义的字符宽度 8mm

c.setFont('华文宋体',15,leading = None) #设定文字字体和字号

# 1. 顶部：标尺粘贴框
y_ruler_start = t_length - p2_top - p2_scale_height
c.rect(p2_left, y_ruler_start, (t_width - p2_left - p2_right - p2_scale_height), p2_scale_height, stroke=1, fill=0)
c.drawString(p2_left + 50 * mm, y_ruler_start + 10, "标  尺  粘  贴")

# 2. 紧接其下：侧掌框 (中间改为 p2_gap_small 间隙)
y_side_start = y_ruler_start - p2_gap_small - p2_side_height
side_box_width = (t_width - p2_left - p2_right - p2_gap_small) / 2
c.rect(p2_left, y_side_start, side_box_width, p2_side_height, stroke=1, fill=0)
c.rect(p2_left + side_box_width + p2_gap_small, y_side_start, side_box_width, p2_side_height, stroke=1, fill=0)

# 文字位置调整到框下方
# 侧掌文字下移，不再位于框内
y_side_text = y_side_start - p2_char_width
c.drawString(p2_left + 10, y_side_text, "左手掌侧面") 
c.drawString(p2_left + side_box_width + p2_gap_small + 10, y_side_text, "右手掌侧面")

# 3. 剩余空间平分为掌纹区域
# 计算剩余高度：文字底部 - 底部边距 - 中间间隙
# 文字底部约为 y_side_text，再保留一点间隙 p2_gap_small
available_height = y_side_text - p2_gap_small - p2_bottom
print_box_height = (available_height - 1 * mm) / 2  # 上下两个掌纹框，中间留 1mm 间隙

# 下方掌纹框 (右手掌纹)
y_print_bottom = p2_bottom
c.rect(p2_left, y_print_bottom, (t_width - p2_right - p2_left - p2_char_width), print_box_height, stroke=1, fill=0)
c.rect(p2_left + (t_width - p2_right - p2_left - p2_char_width), y_print_bottom, p2_char_width, print_box_height, stroke=1, fill=0)

# "右手掌纹" 竖排文字居中
text_x = p2_left + 5 + (t_width - p2_right - p2_left - p2_char_width)
text_center_y = y_print_bottom + print_box_height / 2
c.drawString(text_x, text_center_y + 3 * p2_char_width, "右")
c.drawString(text_x, text_center_y + 1 * p2_char_width, "手")
c.drawString(text_x, text_center_y - 1 * p2_char_width, "掌")
c.drawString(text_x, text_center_y - 3 * p2_char_width, "纹")

# 上方掌纹框 (左手掌纹)
y_print_top = y_print_bottom + print_box_height + 1 * mm
c.rect(p2_left, y_print_top, (t_width - p2_right - p2_left - p2_char_width), print_box_height, stroke=1, fill=0)
c.rect(p2_left + (t_width - p2_right - p2_left - p2_char_width), y_print_top, p2_char_width, print_box_height, stroke=1, fill=0)

# "左手掌纹" 竖排文字居中
text_center_y_top = y_print_top + print_box_height / 2
c.drawString(text_x, text_center_y_top + 3 * p2_char_width, "左")
c.drawString(text_x, text_center_y_top + 1 * p2_char_width, "手")
c.drawString(text_x, text_center_y_top - 1 * p2_char_width, "掌")
c.drawString(text_x, text_center_y_top - 3 * p2_char_width, "纹")

c.save()

