<!-- markdownlint-disable MD033 MD036 MD041  -->
<div align="center">
  <a href="https://v2.nonebot.dev/store">
    <img src="./img/NoneBotPlugin.png" width="300" alt="logo" />
  </a>


# nonebot_plugin_web_bottle
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![PyPI - Version](https://img.shields.io/pypi/v/nonebot-plugin-web-bottle)
[![pdm-managed](https://img.shields.io/endpoint?url=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2Fpdm-project%2F.github%2Fbadge.json)](https://pdm-project.org)

✨一个基于nonebot2与onebotv11 使用fastapi驱动的漂流瓶插件，有一个简单的web用于审核用户提交的漂流瓶✨


</div>


# 如何安装？
（建议使用pip下载后手动在github页面下载源代码并将插件放入插件目录中以使用最新的更改）
**Pypi**
```bash
pip install nonebot-plugin-web-bottle
```

**Nonebot**
```bash
nb plugin install nonebot-plugin-web-bottle
```

# 目前实现了什么？
- [x] 在QQ内
- [x] 丢瓶子
- [x] 捡瓶子
- [x] 评论漂流瓶 [编号] [评论内容]
- [x] 点赞漂流瓶 [编号]
- [x] 在网页端
- [x] 审核漂流瓶
- [x] 审核评论
- [x] 登录验证

# 效果图：
![Image of Yaktocat](https://raw.githubusercontent.com/luosheng520qaq/nonebot-plugin-web-bottle/refs/heads/master/B66FEE6EE4B550CF930CF48FFB9EDC0D.png)
![Image of Yaktocat](https://github.com/luosheng520qaq/nonebot_plugin_web_bottle/blob/master/example/bottles.png)
![Image of Yaktocat](https://github.com/luosheng520qaq/nonebot_plugin_web_bottle/blob/master/example/comments.png)
# 关于插件的其他注意事项
## 存储位置
本插件使用商店的 plugin-localstore(https://github.com/nonebot/plugin-localstore)
默认存储地址请前往其文档查看。
可以自己配置到机器人主目录，方便后续随时查看
```
localstore_cache_dir=   
localstore_config_dir=
localstore_data_dir=
```
在这个插件里，你通常只需要配置修改 localstore_data_dir=  即可

## 建议nonebot配置
如果想要在其他机器上访问到审核web，请修改nonebot运行的IP，在配置文件中修改如下：

```
HOST=0.0.0.0
```

## web页面地址：
```
http://location:nonebot端口/login 登录页面
http://location:nonebot端口/check 漂流瓶审核
http://location:nonebot端口/comments 评论审核

或者将location替换为nonebot所在机器的IPv4地址
```
## 背景图片
位于：
```
插件目录\templates\static\images
```
可自行修改，修改时请修改相应的webp图片
## 关于漂流瓶配置选项：
为防止过多读取时内存占用过高，一个瓶子内最多允许有两张图片，如果需要更多，请在nonebot配置项写入 

以下配置为插件默认值，如果您认为不需要修改，可以不添加
```
# 网页相关
默认登录密钥
bottle_account = 'admin'
bottle_password = 'password'
expire_time=12  # 登录态过期时间（单位：小时）
gzip_level=9    # gzip压缩等级（一般情况无需修改）


# 丢瓶子规则配置
max_bottle_pic=2    # 丢瓶子允许最多图片数量
max_bottle_liens=9  # 丢瓶子允许最多文字行数
max_bottle_word=1200    # 丢瓶子允许最多字符数量
embedded_help=True  # 开启后，丢瓶子时未添加任何内容，则返回指令帮助

# 瓶子评论区规则配置
default_nickname="未知昵称" # 定义获取昵称失败时对评论区用户默认称呼
bottle_msg_split=True   # 分离瓶子和评论区为两条独立消息
max_bottle_comments=3   # 捡瓶子最多展示评论条数

# 适配官方Bot或提升响应速度
bottle_msg_uname=True   # 为False时关闭发送者昵称获取展示 适用于官方Bot或想要提高响应速度时
bottle_msg_gname=True   # 为False时关闭群聊昵称获取展示 同上
qq_markdown=False   # QQMD适配，请自行申请并修改to_msg.py中的模板

```

官方bot仅试过使用 [Gensokyo](https://github.com/Hoshinonyaruko/Gensokyo) 正常运行，野生机器人推荐使用NapCat，LLOneBot ,Lagrange 等

以下是适合本项目的markdown模板和实际效果展示，你需要在QQ开放平台>bot>开发>高阶能力下进行申请，过审后将平台分配的模板ID填写在本项目的tomsg.py模块中（此外，涉及模板图片和头像获取转换，您还需要参考Gensokyo接口文档，在本模块内填写所需IP和端口）：
<table>
  <tr>
    <td>
      <img src="https://github.com/youlanan/nonebot-plugin-web-bottle/blob/master/example/md02.png" width="240" height="160">
      <br>瓶子本体
    </td>
    <td rowspan="2"><img src="https://github.com/youlanan/nonebot-plugin-web-bottle/blob/master/example/md03.jpg" width="240" height="480"></td>
  </tr>
  <tr>
    <td>
      <img src="https://github.com/youlanan/nonebot-plugin-web-bottle/blob/master/example/md01.png" width="240" height="240">
      <br>评论区
    </td>
  </tr>
</table>




# 未来计划
- [x] 提交至nonebot商店 
- [x] 修改漂流瓶投掷者输出方式为 QQ昵称 与 群昵称（已经编写 具体适配情况取决于你的协议端）
- [x] 针对使用QQ开放平台BOT的场景进行调整（支持Gensokyo项目的适配）
- [x] 增加登录验证
- [ ] 新增提醒
- [ ] 美化页面 （等几百年后我学会css再说吧）
- [ ] 优化性能
