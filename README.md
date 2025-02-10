# WOSArticleScraper
先从谷歌学术爬取某个作者的所有文章及文章部分信息，然后通过WOS爬取文章的完整信息。

python代码小白第一次做小项目，如有错漏轻喷。

想做这个项目的动力来自于躺在邮箱里那大几百封未读的谷歌快讯邮件。当看的文献多起来，就学会了用谷歌快讯追踪大佬的动态。追踪的大佬越来越多，文献越发看不完——看着邮箱日渐增长的数字，不知道哪篇和自己领域相关，哪篇是大佬开拓的新方向。有的时候看了几篇非常重要的老文献，关闭窗口之前瞄了一眼作者栏才发现这里面有同一个作者参与——有的是一作，有的是其他作者，有的已经是通讯作者。
对于研究者来说，发表的作品就像他们的孩子一样。有的是精心打磨严厉管教的，有的则是漫不经心随手一挥的。我们这些后辈，这些求学者，则可以通过这些作品悄然窥见他们人生的一些细节（如果我们看得足够多且记得住的话）。
所以我诞生了做这个念头：爬取大佬的所有文章，宏观得分析他们的成果。这个项目就是完成第一步的结果。
分析大佬的成果，相关代码还在编写，但不一定会发上来。目前我预计从多个维度展开。分析发文数量与时间的关系；分析研究主题的分布与变化；分析他们的合作网络；分析他们的发文策略期刊选择（毕竟如果是某期刊的编辑的话……）；分析他们的作者地址等等。
这个项目的代码借助了AI进行编写。DeepSeek-R1真强，虽然总是服务器繁忙，但考虑问题全面，提供的建议好用，逻辑性比其他的要强。希望国产AI再接再厉！
做这个项目痛并快乐着，学到了不少东西。生命不息，学习不止！


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


二、代码逻辑
main.py为主函数文件，其中有三个主函数main_run_all、main_scholarly_only、main_start_by_csv。第一种相当于第二+第三。
首先调用scholarly_utils.py中的get_author_publications函数，获得谷歌学术库给的某大佬的所有文章（科学上网），输出为一个CSV（后缀original，格式为utf-8-sig）。主函数读取csv_original（只读）的所有标题，一个个输入WOSArticleScraper.py，用Chrome打开WOS网页（模拟人的点击，不是发包），输入标题搜索，搜索不到全部赋None。搜索到了进行数量判定，点击进入详情页，比对标题，收集详情，返回details值。每5篇保存一次，得到all_csv。最终处理文件时，把搜索失败的、标题比对失败的清除，得到clean_csv。这些被清除掉的，需要人工复核的，保存abandon_csv。


三、运行注意事项

1. 运行main函数需要检查：
1) author_name
2) last_name（中文作者需要手动设置）
3)运行main函数的哪一种？共有三种main_run_all、main_scholarly_only、main_start_by_csv。最后一种要注意original_csv的设置（注意输入的是all（断点续传）还是original（从零开始））

2. 被scholarly关小黑屋的时长大概是一天；被WOS关小黑屋的时长大约是半天

3. 无头模式会更快，但早期运行最好还是有头检验

4. 超过五百条建议分批搜索

5. 有的WOS网页一打开就要处理cookie，有的WOS网页进入搜索页面才需要处理cookie。自行在WOSArticleScraper.py中的search_article函数中调整cookie位置

6. 去掉国家为None的记录实际上是去掉标题比对失败的记录

7. 如果无论搜索数量多少，反复卡在无法进入详情页，可能是打开的网页页面太小，无法定位到元素，也就无法滚动。理论上切换成无头模式就没问题。

8. 有的时候捕捉作者地址失败，导致这一有效数据行被清除，不在最终的clean_csv中呈现。只能手动从all_csv中复制过来。

9. 如果能搜索到文章，标题比对通过，但是DOI和country都为None，可能是点击成了其他会议文章。如果标题比对不通过，会出现pandas警告，暂时不想管，等出问题再说
