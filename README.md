# WOSArticleScraper
先从谷歌学术爬取某个作者的所有文章及文章部分信息，然后通过WOS爬取文章的完整信息。

代码小白第一次做小项目，如有错漏轻喷。


一、环境配置

1. 软件：
   
Chrome

Python（服务器需要用管理员账号安装）

VS Code
还需插件：中文标点符号转英文；Black Formatter；Chinese (Simplified) (简体中文) Language Pack for Visual Studio Code；Python

2. 安装所需的库（需先安装Python）

pandas: 用于数据处理和CSV文件操作。
selenium: 用于网页抓取和自动化浏览器操作。
scholarly: 用于与Google Scholar的交互。

CMD打开命令提示符，输入下列代码安装库：
pip install pandas selenium scholarly


二、运行注意事项

运行main函数需要检查三项：
1. author_name
2. last_name（中文作者建议手动设置）
3. 运行main函数的哪一种？共有三种main_run_all、main_scholarly_only、main_start_by_csv。最后一种要注意original_csv的设置（注意输入的是all（断点续传）还是original（从零开始））

被scholarly关小黑屋的时长大概是一天；被WOS关小黑屋的时长大约是半天

无头模式会更快，但早期运行最好还是有头检验

超过五百条建议分批搜索

有的WOS网页一打开就要处理cookie，有的WOS网页进入搜索页面才需要处理cookie。自行在WOSArticleScraper.py中的search_article函数中调整cookie位置

去掉国家为None的记录实际上是去掉标题比对失败的记录

如果无论搜索数量多少，反复卡在无法进入详情页，可能是打开的网页页面太小，无法定位到元素，也就无法滚动。理论上切换成无头模式就没问题。

有的时候捕捉作者地址失败，导致这一有效数据行被清除，不在最终的clean_csv中呈现。只能手动从all_csv中复制过来。
如果能搜索到文章，标题比对通过，但是DOI和country都为None，可能是点击成了其他会议文章。
如果标题比对不通过，会出现pandas警告，暂时不想管，等出问题再说。

