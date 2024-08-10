from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    
    # 丢瓶子规则配置
    max_bottle_pic: int = 2    # 丢瓶子允许最多图片数量
    max_bottle_liens: int = 9  # 丢瓶子允许最多文字行数
    max_bottle_word: int = 1200    # 丢瓶子允许最多字符数量
    embedded_help: bool = True  # 开启后，丢瓶子时未添加任何内容，则返回指令帮助

    # 瓶子评论规区则配置
    default_nickname: str = "未知昵称" # 定义获取昵称失败时对评论区用户默认称呼
    bottle_msg_split: bool = True   # 分离瓶子和评论区为两条独立消息
    max_bottle_comments: int = 3   # 捡瓶子最多展示评论条数

    # 适配官方Bot或提升响应速度
    bottle_msg_uname: bool = True   # 为False时关闭发送者昵称获取展示 适用于官方Bot或想要提高响应速度时
    bottle_msg_gname: bool = True   # 为False时关闭群聊昵称获取展示 同上
    qq_open_bot: bool = False    # 是否为官方Bot，野生请填False
    qq_markdown: bool = False   # QQMD适配，请自行申请并修改to_msg.py中的模板



config = get_plugin_config(Config)


max_bottle_pic = config.max_bottle_pic
'''一个瓶子最大的图片数量'''
max_bottle_liens = config.max_bottle_liens
'''一个瓶子的最大换行长度'''
max_bottle_word = config.max_bottle_word
'''瓶子内容最多允许的字数'''
max_bottle_comments = config.max_bottle_comments
'''单个瓶子捡取时展示的最大评论数量'''


bottle_msg_uname = config.bottle_msg_uname
'''启用漂流瓶玩家昵称获取展示'''
bottle_msg_gname = config.bottle_msg_gname
'''启用漂流瓶群昵称获取展示（同上）'''
default_nickname = config.default_nickname
'''定义的默认昵称'''


bottle_msg_split = config.bottle_msg_split
'''瓶子本体内容与评论分段发送'''
embedded_help = config.embedded_help
'''在丢瓶子未填写内容时回复帮助文本'''
qq_open_bot = config.qq_open_bot
'''官方Bot适配'''
qq_markdown = config.qq_markdown
'''官方MD适配'''