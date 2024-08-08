from nonebot import get_driver
from pydantic import Extra, BaseModel


class Config(BaseModel, extra=Extra.ignore):
    # 一个瓶子最大的图片数量
    max_bottle_pic: int = 2
    # 一个瓶子的最大换行长度
    max_bottle_liens: int = 9
    # 单个瓶子捡取时展示的最大评论数量
    max_bottle_comments: int = 3


config = Config.parse_obj(get_driver().config.dict())
max_bottle_pic = config.max_bottle_pic
max_bottle_liens = config.max_bottle_liens
max_bottle_comments = config.max_bottle_comments
