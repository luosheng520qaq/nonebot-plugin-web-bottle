from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    # 一个瓶子最大的图片数量
    max_bottle_pic: int = 2
    # 一个瓶子的最大换行长度
    max_bottle_liens: int = 9
    # 瓶子内容最多允许的字数
    max_bottle_word: int = 1200
    # 单个瓶子捡取时展示的最大评论数量
    max_bottle_comments: int = 3
    
    # 启用漂流瓶玩家昵称获取展示
    # （例如官方Bot等获取不到昵称，且ID无意义的情况下，可以关闭获取以加快响应速度）
    bottle_msg_uname: bool = True
    # 启用漂流瓶群昵称获取展示（同上）
    bottle_msg_gname: bool = True
    # 定义默认昵称
    default_nickname: str = "未知昵称"
    
    # 瓶子本体内容与评论分段发送
    bottle_msg_split: bool = True
    # 在丢瓶子未填写内容时回复帮助文本
    embedded_help: bool = True
    # QQ开放平台的bot请启用
    qq_open_bot: bool = True
    # QQ通过的MD适配
    # 请根据自己申请的MD自行修改to_msg中MD模板格式
    qq_markdown: bool = False


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
