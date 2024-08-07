from nonebot.plugin import PluginMetadata
from nonebot import on_command, on_fullmatch, get_driver, get_app
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, Bot, MessageSegment
from nonebot.params import CommandArg
from nonebot.log import logger
from . import sqlite3
import base64
from .web_bottle import Bottle, id_add,serialize_message
import re
from datetime import datetime, timedelta


__plugin_meta__ = PluginMetadata(
    name="漂流瓶",
    description="一个基于nonebot2与onebotv11 使用fastapi驱动的漂流瓶插件，有一个简单的web用于审核用户提交的漂流瓶",
    usage="详细见 https://github.com/luosheng520qaq/nonebot_plugin_web_bottle",
    type="application",
    homepage="https://github.com/luosheng520qaq/nonebot_plugin_web_bottle",
    extra={},
)



throw = on_command("丢瓶子", aliases={"扔瓶子"}, priority=1, block=True)
get_bottle = on_fullmatch("捡瓶子", priority=1, block=True)
up_bottle = on_command("点赞漂流瓶", priority=1, block=True)
comment = on_command("评论漂流瓶", priority=1, block=True)
read_bottle = on_command("查看漂流瓶", priority=1, block=True)


@read_bottle.handle()
async def _(bot: Bot, event: GroupMessageEvent, foo: Message = CommandArg()):
    try:
        a = int(foo.extract_plain_text())
    except:
        await read_bottle.finish("请输入正确的漂流瓶id")
    bottle = Bottle(sqlite3.conn_bottle)
    b = await bottle.get_approved_bottle_by_id(a)
    if b == None:
        cursor = sqlite3.conn_bottle.cursor()
        query = """
            SELECT state
            FROM pending
            WHERE id = ?
        """

        # 执行查询
        cursor.execute(query, (a,))

        # 获取查询结果
        result = cursor.fetchone()

        # 关闭游标
        cursor.close()

        # 返回查询结果，如果没有找到则返回None
        c = result[0]
        if c == 100:
            await read_bottle.finish("漂流瓶已拒绝无法查看！")
        elif c == 0:
            await read_bottle.finish("漂流瓶未审核")
        else:
            await read_bottle.finish("发生未知错误！")
    img_bytes_list = await bottle.get_bottle_images(b['id'])
    j = await bot.call_api(api="get_stranger_info", **{
        'user_id': int(b['userid'])
    })

    n = await bot.call_api(api="get_group_info", **{
        'group_id': int(b['groupid'])
    })

    sender_nickname = j['nickname']
    group_name = n['group_name']

    # 创建消息段
    message = Message(
        f"捡到漂流瓶id：{b['id']}\n"
        f"内容：{b['content']}\n"
        f"发送者：{sender_nickname}\n"
        f"发送群：{group_name}\n"
        f"发送时间：{b['timeinfo']}\n"
    )


    # 添加图片到消息中
    for img_bytes in img_bytes_list:
        # 将字节转换为 base64 编码的字符串
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        # 创建 MessageSegment 对象
        img_segment = MessageSegment.image(f'base64://{img_base64}')
        # 将图片添加到消息中
        message += img_segment
    comments = await bottle.get_comments(int(b['id']))

    # 初始化新的字符串
    formatted_comments = ""

    # 分割字符串以获取每条评论
    comment_lines = comments.split('\n')

    # 处理每条评论
    for line in comment_lines:
        # 分割每条评论以获取 ID 和消息
        id_and_comment = line.split(': ')
        if len(id_and_comment) == 2:
            user_id, comment = id_and_comment[0], ': '.join(id_and_comment[1:])
            try:
                # 调用 API 获取用户信息
                j = await bot.call_api("get_stranger_info", **{
                    'user_id': int(user_id)
                })

                # 获取成员的昵称
                name = j.get('nickname', '未知昵称')

                # 构造昵称和评论的格式化字符串并添加到 formatted_comments 中
                formatted_comments += f"{name}: {comment}\n"
            except Exception as e:
                # 如果 API 调用失败，则使用默认昵称
                formatted_comments += f"未知昵称: {comment}\n"
    message += Message(formatted_comments)

    # 发送消息
    await read_bottle.finish(message)



@comment.handle()
async def _(bot: Bot, event: GroupMessageEvent, foo: Message = CommandArg()):
    try:
        a = str(foo).split()
        bottle_id = int(a[0])
        text = str(a[1])
    except:
        await comment.finish("请输入正确的漂流瓶id和评论内容")
    bottle = Bottle(sqlite3.conn_bottle)
    a = await bottle.add_comment_if_approved(bottle_id, text, event.user_id)
    if not a:
        await comment.finish("评论失败，漂流瓶不存在")
    else:
        await comment.finish("评论成功！")


@up_bottle.handle()
async def _(bot: Bot, event: GroupMessageEvent, foo: Message = CommandArg()):
    try:
        foo = int(foo.extract_plain_text())
    except:
        await up_bottle.finish("请输入正确的漂流瓶id")
    bottle = Bottle(sqlite3.conn_bottle)
    a, num = await bottle.up_bottle(foo, event.user_id)
    if not a:
        await up_bottle.finish("点赞失败，漂流瓶不存在或你已经点赞过了")
    else:
        await up_bottle.finish(f"点赞成功,现在有{num}个赞！")


@get_bottle.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    await get_bottle.send("捡瓶子中...")
    bottle = Bottle(sqlite3.conn_bottle)
    bottle_data = await bottle.random_get_approves_bottle()
    if not bottle_data:
        await get_bottle.finish("捞瓶子失败，没有漂流瓶~")
    img_bytes_list = await bottle.get_bottle_images(bottle_data['id'])

    j = await bot.call_api(api="get_stranger_info", **{
        'user_id': int(bottle_data['userid'])
    })

    n = await bot.call_api(api="get_group_info", **{
        'group_id': int(bottle_data['groupid'])
    })

    sender_nickname = j['nickname']
    group_name = n['group_name']
    # 创建消息段
    message = Message(
        f"捡到漂流瓶id：{bottle_data['id']}\n"
        f"内容：{bottle_data['content']}\n"
        f"发送者：{sender_nickname}\n"
        f"发送群：{group_name}\n"
        f"发送时间：{bottle_data['timeinfo']}\n"
    )

    # 添加图片到消息中
    for img_bytes in img_bytes_list:
        # 将字节转换为 base64 编码的字符串
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        # 创建 MessageSegment 对象
        img_segment = MessageSegment.image(f'base64://{img_base64}')
        # 将图片添加到消息中
        message += img_segment
    comments = await bottle.get_comments(int(bottle_data['id']))

    # 分割字符串以获取每条评论
    comment_lines = comments.split('\n')

    # 初始化新的字符串
    formatted_comments = ""

    # 初始化计数器
    comment_count = 0
    max_bottles_comments = get_driver().config.dict().get("max_bottle_comment", 3)
    # 处理每条评论
    for line in comment_lines:
        # 分割每条评论以获取 ID 和消息
        id_and_comment = line.split(': ')
        if len(id_and_comment) == 2 and comment_count <= max_bottles_comments:
            user_id, comment = id_and_comment[0], ': '.join(id_and_comment[1:])

            try:
                # 调用 API 获取用户信息
                j = await bot.call_api("get_stranger_info", **{
                    'user_id': int(user_id)
                })

                # 获取成员的昵称
                name = j.get('nickname', '未知昵称')

                # 构造昵称和评论的格式化字符串并添加到 formatted_comments 中
                formatted_comments += f"{name}: {comment}\n"
            except Exception as e:
                # 如果 API 调用失败，则使用默认昵称
                formatted_comments += f"未知昵称: {comment}\n"

            # 增加计数器
            comment_count += 1
    message += Message(formatted_comments)
    # 发送消息
    await get_bottle.finish(message)


@throw.handle()
async def _(bot: Bot, event: GroupMessageEvent, foo: Message = CommandArg()):
    if not foo:
        await throw.finish("丢瓶子需要输入内容哦~")
    else:
        foo = foo.extract_plain_text().strip()
        # 匹配 \n, \r\n 和 \r
        newline_pattern = r'[\r\n]+'
        number_contains = len(re.findall(newline_pattern, foo))
        n = get_driver().config.dict().get("max_bottle_liens", 9)
        if number_contains >= n:
            await throw.finish("丢瓶子内容过长，请不要超过9行哦~")
        id = await id_add()
        id = int(id)
        conn = sqlite3.conn_bottle
        ms = event.get_message()
        content = await serialize_message(ms, id, conn)
        bottle = Bottle(conn)
        time_info = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        a = await bottle.add_pending_bottle(id, foo, event.user_id, event.group_id, time_info)
        if a:
            await throw.finish(f"丢瓶子成功，请等待管理员审核~、id:{id}")
