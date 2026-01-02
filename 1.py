import cv2
 
class CutImg:
    """
    识别答题卡答题区域工具类
        资料: https://weread.qq.com/web/reader/30232de0719146363020e69kc81322c012c81e728d9d180
             https://blog.csdn.net/qq_33897832/article/details/88931748
             https://blog.csdn.net/qq_34062754/article/details/86639216  图像的模糊处理
        处理过程:
            1. 读取图片
            2. 图像平滑处理
            3. 图像阈值处理
            4. 图像轮廓
            5. 裁剪对比原图面积比在 小于0.8 大于0.05 图像保留
        暂留代码块
        # 中值滤波
        # thd1 = cv2.medianBlur(thd1, 7)
        # cv2.imshow('mediu', thd1)
        # cv2.waitKey(0)
        # 查找轮廓
        # cnts, hierarchy = cv2.findContours(thd1, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        # img = cv2.drawContours(image, cnts, -1, (0, 0, 255), 3)
        # cv2.imshow('hierarchy', img)
        # cv2.waitKey(0)
    """
 
    def __init__(self, path):
        """
        @param path: 待处理答题卡图片路径
        """
        self.img_data = cv2.imread(path, 0)
        self.process_img = None  # 处理中答题卡图片数据
 
    def process(self):
        """
        图像平滑处理
        图像阈值处理
        @return:
        """
        # retval代表返回的阈值  dst代表阈值分割结果图像，与原始图像具有相同的大小和类型
        # thresh代表要设定的阈值
        # maxval代表当type参数为THRESH_BINARY或者THRESH_BINARY_INV类型时，需要设定的最大值
        retval, dst = cv2.threshold(self.img_data, thresh=250, maxval=255, type=cv2.THRESH_BINARY)
        # 图像平滑处理: 高斯滤波
        # ksize是滤波核的大小。滤波核大小是指在滤波处理过程中其邻域图像的高度和宽度。需要注意，滤波核的值必须是奇数
        dst = cv2.GaussianBlur(dst, ksize=(31, 31), sigmaX=0, sigmaY=0)
        # 针对图像平滑处理再次阈值处理
        retval, dst = cv2.threshold(dst, 250, 255, cv2.THRESH_BINARY)
 
        self.process_img = dst
        return self
 
    def save(self):
        """
        保存答题区域
            图像轮廓
            裁剪对比原图面积比在 小于0.8 大于0.05 图像保留
            @todo 可以将裁剪图片转成字节流转base64 保存数据库, 前端将base64转换成图片格式
        @return:
        """
        # cv2.RETR_CCOMP 检索所有轮廓并将它们组织成两级层次结构
        cnts, hierarchy = cv2.findContours(self.process_img, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        for c, i in zip(cnts, hierarchy[0]):
            x, y, w, h = cv2.boundingRect(c)  # 包覆此轮廓的最小正矩形
            ROI = self.img_data[y:y + h, x:x + w]
            # if 0.8 > ROI.size / self.img_data.size > 0.05:  # 小于0.8 大于0.05面积比=>图像保留
            #     cv2.imwrite("./{}.png".format(i), ROI)
            cv2.imwrite("./{}.png".format(i), ROI)
                
 
 
if __name__ == '__main__':
    import time
    s = time.time()
    path = "image-2.png"  # 读取图像文件夹
    for _ in range(1000):
        c = CutImg(path)
        c.process().save()
    print(time.time()-s)