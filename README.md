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

以下配置为插件默认值，如果您认为不需要修改，可以不添加
```
# 丢瓶子规则配置
max_bottle_pic=2    # 丢瓶子允许最多图片数量
max_bottle_liens=9  # 丢瓶子允许最多文字行数
max_bottle_word=1200    # 丢瓶子允许最多字符数量
embedded_help=True  # 开启后，丢瓶子时未添加任何内容，则返回指令帮助

# 瓶子评论规区则配置
default_nickname="未知昵称" # 定义获取昵称失败时对评论区用户默认称呼
bottle_msg_split=True   # 分离瓶子和评论区为两条独立消息
max_bottle_comments=3   # 捡瓶子最多展示评论条数

# 适配官方Bot或提升响应速度
bottle_msg_uname=True   # 为False时关闭发送者昵称获取展示 适用于官方Bot或想要提高响应速度时
bottle_msg_gname=True   # 为False时关闭群聊昵称获取展示 同上
qq_open_bot=False    # 是否为官方Bot，野生请填False
qq_markdown=False   # QQMD适配，请自行申请并修改to_msg.py中的模板
```
# 未来计划
- [ ] 新增一个网页填入id查看漂流瓶详情
- [✓] 修改漂流瓶投掷者输出方式为 QQ昵称 与 群昵称（已经编写 具体适配情况取决于你的协议端）
- [ ] 美化页面 （等几百年后我学会css再说吧）
- [✓] 提交至nonebot商店 
- [ ] 优化性能
- [ ] 针对使用QQ开放平台BOT的场景进行调整（目前已支持关闭传统昵称获取）
