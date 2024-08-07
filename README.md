# nonebot_plugin_web_bottle
# 这是什么？
一个基于nonebot2与onebotv11 使用fastapi驱动的漂流瓶插件，有一个简单的web用于审核用户提交的漂流瓶
# 如何安装？
使用pip或者nb指令
```
pip install nonebot-plugin-web-bottle

nb plugin install nonebot-plugin-web-bottle
```
# 目前实现了什么？
## 在QQ内
### 丢瓶子
### 捡瓶子
### 评论漂流瓶 [编号] [评论内容]
### 点赞漂流瓶 [编号]
## 在网页端
### 审核漂流瓶
### 审核评论
# 效果图：
![Image of Yaktocat](https://github.com/luosheng520qaq/nonebot_plugin_web_bottle/blob/master/example/bottles.png)
![Image of Yaktocat](https://github.com/luosheng520qaq/nonebot_plugin_web_bottle/blob/master/example/comments.png)
# 关于插件的其他注意事项
## 存储位置
本插件使用商店的 plugin-localstore(https://github.com/nonebot/plugin-localstore)
默认存储地址请前往其文档查看。
可以自己配置到机器人主目录，挡板后续随时查看
```
localstore_cache_dir=   
localstore_config_dir=
localstore_data_dir=
```
在这个插件里，你通常只需要配置修改 localstore_data_dir=即可
## web页面地址：
```
http://location:nonebot端口/check 漂流瓶审核

http://location:nonebot端口/comments 评论审核
```
## 背景图片
位于：
```
插件目录\templates\static\images
```
可自行修改
## 关于漂流瓶配置文件：
为防止过多读取时内存占用过高，一个瓶子内最多允许有两张图片，如果需要更多，请在nonebot配置项写入 
```
max_bottle_pic = 
```
漂流瓶的最长列数量默认为9行
```
max_bottle_liens = 
```
单个漂流瓶显示的评论数量，默认为3
```
max_bottle_comments = 
```
# 未来计划
- [ ] 新增一个网页填入id查看漂流瓶详情
- [✓] 修改漂流瓶投掷者输出方式为 QQ昵称 与 群昵称（已经编写 具体适配情况取决于你的协议端）
- [ ] 美化页面 （等几百年后我学会css再说吧）
- [✓] 提交至nonebot商店 
- [ ] 优化性能
