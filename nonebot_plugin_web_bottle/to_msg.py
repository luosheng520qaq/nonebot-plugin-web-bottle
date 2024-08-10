import base64
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from .config import (
    max_bottle_comments,
    bottle_msg_uname,
    bottle_msg_gname,
    default_nickname,
    bottle_msg_split,
    qq_open_bot,
    qq_markdown
    )



async def get_bottle_info(bot: Bot, bottle_data: dict) -> str:
    '''
    获取瓶子内容文本和用户信息
    '''
    message = f"漂流瓶ID：{bottle_data['id']}\n"
    message += f"内容：{bottle_data['content']}\n"
    async def get_uname():
        try:
            j = await bot.call_api(api="get_stranger_info", user_id=int(bottle_data["userid"]))
            return j["nickname"]
        except:  # TODO)): 只抓需要的 Error  # noqa: E722
            return str(bottle_data["userid"])
    async def get_gname():
        try:
            n = await bot.call_api(api="get_group_info", group_id=int(bottle_data["groupid"]))
            return n["group_name"]
        except:  # TODO)): 只抓需要的 Error  # noqa: E722
            return str(bottle_data["groupid"])
    if bottle_msg_uname:
        message += f"发送者：{await get_uname()}\n"
    if bottle_msg_gname:
        message += f"发送群：{await get_gname()}\n"
    message += f"发送时间：{bottle_data['timeinfo']}"
    return message
    


async def get_bottle_img(message: Message, img_bytes_list: dict) -> Message:
    '''
    添加图片到消息中
    '''
    for img_bytes in img_bytes_list:
        # 将字节转换为 base64 编码的字符串
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        # 创建 MessageSegment 对象
        img_segment = MessageSegment.image(f"base64://{img_base64}")
        # 将图片添加到消息中
        message += img_segment
    return message



async def get_bottle_comment(bot: Bot, comments: str, bid) -> str:
    '''
    格式化瓶子的评论
    '''
    if not comments:
        return ''
    # 分割字符串以获取每条评论
    comment_lines = comments.split("\n")

    # 初始化新的字符串
    if bottle_msg_split:
        formatted_comments = f"漂流瓶 {bid} 的评论区\n"
    else:
        formatted_comments = "评论区：\n"

    # 初始化计数器
    comment_count = 0
    max_bottles_comments = max_bottle_comments
    # 处理每条评论
    for line in comment_lines:
        # 分割每条评论以获取 ID 和消息
        id_and_comment = line.split(": ")
        if len(id_and_comment) == 2 and comment_count <= max_bottles_comments:  # noqa: PLR2004
            user_id, comment = id_and_comment[0], ": ".join(id_and_comment[1:])

            if bottle_msg_uname:
                try:
                    # 调用 API 获取用户信息
                    j = await bot.call_api("get_stranger_info", user_id=int(user_id))
                    # 获取成员的昵称
                    name = j.get("nickname", default_nickname)
                    # 构造昵称和评论的格式化字符串并添加到 formatted_comments 中
                    formatted_comments += f"{name}: {comment}\n"
                except Exception:  # TODO)): 只抓需要的 Error  # noqa: BLE001
                    # 如果 API 调用失败，则使用默认昵称
                    formatted_comments += f"{default_nickname}: {comment}\n"
            else:
                formatted_comments += f"- {comment}\n"

            # 增加计数器
            comment_count += 1
    return formatted_comments