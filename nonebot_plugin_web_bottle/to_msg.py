from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from .web_bottle import Bottle
from .config import Config
import nonebot

from PIL import Image

import base64
import httpx
import json
import io

driver = nonebot.get_driver()
global_config = driver.config
config = Config.parse_obj(global_config)
max_bottle_comments = config.max_bottle_comments
bottle_msg_uname = config.bottle_msg_uname
bottle_msg_gname = config.bottle_msg_gname
bottle_msg_split = config.bottle_msg_split
default_nickname = config.default_nickname
qq_markdown = config.qq_markdown

# require("Tea_你好茶茶")
# require("Tea_API")
# from src.core.Tea_你好茶茶 import 玩家昵称接口
# from src.core.Tea_API import 停用MD, ServerAPI
ServerAPI = "127.0.0.1:8080"  # 请参考Gensokyo文档进行接口配置
MDID01 = "000000000_0000000000"
MDID02 = "000000001_0000000001"


# 以下为普通消息处理
async def get_botte_all(bot: Bot, bottle_data: dict, bottle: Bottle) -> list:
    """
    获取瓶子内容、评论，并以列表形式返回
    """
    message = []

    # 瓶子内容获取
    msg_one = f"漂流瓶ID：{bottle_data['id']}\n内容：{bottle_data['content']}\n"
    if bottle_msg_uname:
        msg_one += f"发送者：{await get_user_name(bot, bottle_data['userid'])}\n"
    if bottle_msg_gname:
        msg_one += f"发送群：{await get_group_name(bot, bottle_data['groupid'])}\n"
    msg_one += f"发送时间：{bottle_data['timeinfo']}"
    msg_one = Message(msg_one)

    # 将图片添加到瓶子内容中
    img_bytes_list = await bottle.get_bottle_images(bottle_data["id"])
    for img_bytes in img_bytes_list:
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        img_segment = MessageSegment.image(f"base64://{img_base64}")
        msg_one += img_segment

    message.append(msg_one)

    # 格式化瓶子评论
    comments = await bottle.get_comments(int(bottle_data["id"]))
    if comments:
        formatted_comments = await format_comments(bot, comments)
        if bottle_msg_split:
            message.append(formatted_comments)
        else:
            message[0] += Message(formatted_comments)

    return message


async def get_user_name(bot: Bot, user_id: int) -> str:
    """
    获取用户昵称
    """
    try:
        user_info = await bot.call_api(api="get_stranger_info", user_id=user_id)
        return user_info["nickname"]
    except:
        return str(user_id)


async def get_group_name(bot: Bot, group_id: int) -> str:
    """
    获取群名称
    """
    try:
        group_info = await bot.call_api(api="get_group_info", group_id=group_id)
        return group_info["group_name"]
    except:
        return str(group_id)


async def format_comments(bot: Bot, comments: str) -> str:
    """
    格式化评论
    """
    comment_lines = comments.split("\n")
    formatted_comments = "评论区：\n"
    comment_count = 0

    for line in comment_lines:
        if comment_count >= max_bottle_comments:
            break
        user_id, comment = line.split(": ", 1)
        user_name = await get_user_name(bot, int(user_id)) if bottle_msg_uname else default_nickname
        formatted_comments += f"{user_name}: {comment}\n"
        comment_count += 1

    return formatted_comments


# 以下为QQMD适配
async def get_botte_tomd(bot: Bot, bottle_data: dict, bottle: Bottle) -> list:
    """
    获取瓶子内容、评论，并以列表形式返回
    ---
    最终内容为符合 Gensokyo 协议端的 markdown segment
    它属于对 onebot v11 的扩展，用以发送 通过QQ开放平台申请的 Markdown模板
    ---
    示例:
    {
        "type": "markdown",
        "data": {
            "data": "文本内容"
        }
    }
    """
    message = []

    # 瓶子本体文本获取
    msg_one = f"Time：{bottle_data['timeinfo']}\rBottle_id：{bottle_data['id']}\r\r{default_nickname}："  # {玩家昵称接口(bottle_data['userid'])}："
    msg_one += bottle_data['content'].replace("\n", "\r") if bottle_data['content'] else "什么都没写"

    # 插入图片部分
    img_bytes_list = await bottle.get_bottle_images(bottle_data["id"])
    if not img_bytes_list:
        message.append(await create_markdown_segment(msg_one))
    else:
        for index, img_bytes in enumerate(img_bytes_list):
            img_b64 = base64.b64encode(img_bytes).decode()
            try:
                w, h = get_image_size(img_bytes)
                img_url = await post_image_to_server(img_b64, f"http://{ServerAPI}/uploadpic")
                if index == 0:
                    message.append(await create_markdown_segment(msg_one, [w, h, img_url]))
                else:
                    message.append(await create_markdown_segment("-", [w, h, img_url]))
            except Exception:
                pass

    # 格式化瓶子评论
    comments = await bottle.get_comments(int(bottle_data["id"]))
    # if comments:
    formatted_comments = await format_comments_md(bot, comments, bottle_data["id"])
    message.append(formatted_comments)

    return message


async def post_image_to_server(base64_image: str, target_url: str) -> str:
    """
    将图片上传到服务器
    """
    data = {'base64Image': base64_image}
    async with httpx.AsyncClient() as client:
        response = await client.post(target_url, data=data)
    if response.status_code != 200:
        raise Exception("Error response from server: {}".format(response.status_code))
    response_data = json.loads(response.text)
    if "url" in response_data:
        return response_data["url"]
    else:
        raise Exception("URL not found in response")


def get_image_size(img_bytes: bytes) -> tuple:
    """
    获取图片尺寸
    """
    with Image.open(io.BytesIO(img_bytes)) as image:
        width, height = image.size
    return str(width), str(height)


async def create_markdown_segment(msg_one: str, img: list = None) -> str:
    """
    创建 Markdown 段落
    """
    if img:
        data = {
            "markdown": {
                "custom_template_id": MDID01,
                "params": [
                    {"key": "w", "values": [img[0]]},
                    {"key": "h", "values": [img[1]]},
                    {"key": "url", "values": [img[2]]},
                    {"key": "msg", "values": [msg_one]}
                ]
            }
        }
    else:
        data = {
            "markdown": {
                "custom_template_id": MDID02,
                "params": [{"key": "msg", "values": [msg_one]}]
            }
        }
    json_str = json.dumps(data)
    encoded_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    return f'[CQ:markdown,data=base64://{encoded_data}]'


async def format_comments_md(bot: Bot, comments: str, bottle_id: int) -> str:
    """
    格式化 Markdown 评论
    """
    comment_lines = comments.split("\n")
    formatted_comments = f"漂流瓶 {bottle_id} 的评论区\r"
    users_avatar = []
    comment_count = 0

    for line in comment_lines:
        if comment_count >= max_bottle_comments:
            break
        id_and_comment = line.split(": ")
        if len(id_and_comment) == 2:
            user_id, comment = id_and_comment[0], ": ".join(id_and_comment[1:])
        else:
            continue
        user_name = 玩家昵称接口(user_id)
        avatar_url = await fetch_avatar_url(user_id)
        users_avatar.append(avatar_url)
        formatted_comments += f"{user_name}: {comment}\r"
        comment_count += 1

    all_user = len(comment_lines)
    default_avatar = "https://tse1-mm.cn.bing.net/th/id/OIP-C.FQeBsP0v7u7cZQO1Z5do9gAAAA?w=34&h=34&c=7&r=0&o=5&dpr=2" \
                     ".5&pid=1.7"
    data = {
        "markdown": {
            "custom_template_id": "102069827_1723800235",
            "params": [
                {"key": "pic1", "values": [users_avatar[0] if len(users_avatar) > 0 else default_avatar]},
                {"key": "pic2", "values": [users_avatar[1] if len(users_avatar) > 1 else default_avatar]},
                {"key": "pic3", "values": [users_avatar[2] if len(users_avatar) > 2 else default_avatar]},
                {"key": "tip", "values": [f"...  共{all_user}条评论~" if all_user else "  还没有内容哦~"]},
                {"key": "msg", "values": [formatted_comments]},
                {"key": "cmd1", "values": ['show="ⓘ" text="漂流瓶帮助"']},
                {"key": "cmd2", "values": ['show="丢瓶子" text="扔瓶子"']},
                {"key": "cmd3", "values": ['show="捡瓶子" text="捡瓶子"']},
                {"key": "cmd4", "values": [f'show="点赞" text="点赞漂流瓶 {bottle_id}"']},
                {"key": "cmd5", "values": [f'show="发评论" text="评论漂流瓶 {bottle_id}"']}
            ]
        }
    }
    json_str = json.dumps(data)
    encoded_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    return f'[CQ:markdown,data=base64://{encoded_data}]'


async def fetch_avatar_url(user_id: str) -> str:
    """
    获取用户头像 URL
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://{ServerAPI}/getid?id={user_id}&type=2")
    response.raise_for_status()
    data = response.json()
    return f"https://q.qlogo.cn/qqapp/102069827/{data.get('id', '')}/640"


async def botte_routing(bot: Bot, bottle_data: dict, bottle: Bottle):
    """
    根据配置选择发送 Markdown 或普通消息
    """
    if qq_markdown:  # and not 停用MD(bottle_data["userid"]):
        return await get_botte_tomd(bot, bottle_data, bottle)
    return await get_botte_all(bot, bottle_data, bottle)
