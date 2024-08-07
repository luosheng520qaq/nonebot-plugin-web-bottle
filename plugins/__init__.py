from nonebot.plugin import PluginMetadata
from . import sqlite3
from . import web_bottle

__plugin_meta__ = PluginMetadata(
    name="漂流瓶",
    description="一个基于nonebot2与onebotv11 使用fastapi驱动的漂流瓶插件，有一个简单的web用于审核用户提交的漂流瓶",
    usage="详细见 https://github.com/luosheng520qaq/nonebot_plugin_web_bottle",
    type="application",
    homepage="https://github.com/luosheng520qaq/nonebot_plugin_web_bottle",
    extra={},
)