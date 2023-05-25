"""1.管理员模式下win+R命令行输入pip install wordcloud;
pip install imageio(用于确定词云形状，可选。我试的时候没有成型效果)
"""
#2.import wordcloud库

import wordcloud

#from imageio.v2 import imread

#3.文件只能使用.txt格式。可以将excel某一列选中复制到新的excel中，另存为.txt格式。
#4.encoding根据文件编码来，我的utf-8不行所以改成了utf-16

# mk=imread("D:\\fivestar.jpg")
f=open("D:\\version1.5.txt","r",encoding="utf-16").read()

#5.创建wordcloud对象，括号内可以加入width，height，font，step,mask等属性进行具体修改

#w=wordcloud.WordCloud(mask=mk)
w=wordcloud.WordCloud()

#6.调用generate方法，参数是一段字符串，将该字符串加入词云

w.generate(f)

#7.生成目标文件

w.to_file("test.png")