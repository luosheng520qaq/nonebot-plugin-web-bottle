# 这是什么？
一个基于nonebot2与onebotv11 使用fastapi驱动的漂流瓶插件，有一个简单的web用于审核用户提交的漂流瓶
# 如何安装？
下载整个仓库，将其解压到你的Bot主目录，并在pyproject.toml文件中修改为如下配置
```
plugin_dirs = ["plugins"]。
```
本插件使用的相关第三方库在requirements.txt中，你可以在解压后在bot主目录运行以下指令即可
```
pip install -r requirements.txt
```
# 目前实现了什么？
## 在QQ内
丢瓶子
捡瓶子
评论漂流瓶 [编号] [评论内容]
点赞漂流瓶 [编号]
## 在网页端
审核漂流瓶
审核评论
# 效果图：
![Image of Yaktocat](https://github.com/luosheng520qaq/nonebot_plugin_web_bottle/blob/master/example/bottles.png)
![Image of Yaktocat](https://github.com/luosheng520qaq/nonebot_plugin_web_bottle/blob/master/example/comments.png)
# 关于插件的其他详细信息
## web页面地址：
```
http://location:nonebot端口/check 漂流瓶审核

http://location:nonebot端口/comments 评论审核
```
## 背景图片
位于：
```
\templates\static\images
```
可自行修改
## 关于漂流瓶图片数量：
为防止过多读取时内存占用过高，一个瓶子内最多允许有两张图片，如果你觉得需要更多，请修改位于plugins/web_bottle.py 的167行代码将if seg.type == "image" and i < 3  # 限制只处理前两张图片中的3改为其他数字
# 未来计划
- [ ] 新增一个网页填入id查看漂流瓶详情
- [ ] 修改漂流瓶投掷者输出方式为 QQ昵称 与 群昵称
- [ ] 美化页面 （等几百年后我学会css再说吧）
- [ ] 提交至nonebot商店 暂时不会QwQ （2024年8月6日） 后面研究一下
- [ ] 优化性能
