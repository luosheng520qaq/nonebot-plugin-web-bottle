from pydantic import BaseModel


class Config(BaseModel):
    # 丢瓶子规则配置
    max_bottle_pic: int = 2  # 丢瓶子允许最多图片数量
    max_bottle_liens: int = 9  # 丢瓶子允许最多文字行数
    max_bottle_word: int = 1200  # 丢瓶子允许最多字符数量
    embedded_help: bool = True  # 开启后，丢瓶子时未添加任何内容，则返回指令帮助
    cooling_time: int = 6  # 默认指令冷却 单位秒
    # 瓶子评论规区则配置
    default_nickname: str = "未知昵称"  # 定义获取昵称失败时对评论区用户默认称呼
    bottle_msg_split: bool = True  # 分离瓶子和评论区为两条独立消息
    max_bottle_comments: int = 3  # 捡瓶子最多展示评论条数

    # 适配官方Bot或提升响应速度
    bottle_msg_uname: bool = True  # 为False时关闭发送者昵称获取展示 适用于官方Bot或想要提高响应速度时
    bottle_msg_gname: bool = True  # 为False时关闭群聊昵称获取展示 同上
    qq_markdown: bool = False  # QQMD适配，请自行申请并修改to_msg.py中的模板
    bottle_account: str = 'admin'
    bottle_password: str = 'password'
    expire_time: int = 12  # 登录态过期时间（单位：小时）

    gzip_level: int = 9
