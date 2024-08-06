from nonebot import on_command, on_fullmatch
from nonebot.adapters.onebot.v11 import Event, Message, GroupMessageEvent, Bot, MessageSegment, GROUP_ADMIN, GROUP_OWNER
from nonebot.params import Matcher, CommandArg, ArgPlainText, EventToMe
import random
from . import sqllite3
from nonebot.log import logger
import datetime
import aiofiles
import asyncio
from nonebot import get_driver, get_app
from datetime import datetime
from typing import Any, Dict
import re
from fastapi import  HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
import base64
import httpx



from sqlite3 import Connection

app = get_app()
driver = get_driver()

app.mount("/static", StaticFiles(directory="./templates/static"), name="static")
templates = Jinja2Templates(directory="templates")


class BottleInfo(BaseModel):
    ID: int
    Content: str
    UserID: int
    GroupID: int
    TimeInfo: str
    State: int
    Images: List[str]


@app.get("/check", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/bottles/random", response_model=BottleInfo)
async def get_random_bottle():
    bottle = Bottle(conn=sqllite3.conn_bottle)
    b = await bottle.random_get_bottle()
    if not b:
        raise HTTPException(status_code=404, detail="No bottles found")

    images = await bottle.get_bottle_images(b["id"])
    images_base64 = [base64.b64encode(img).decode('utf-8') for img in images]

    bottle_info = BottleInfo(
        ID=b["id"],
        Content=b["content"],
        UserID=b["userid"],
        GroupID=b["groupid"],
        TimeInfo=b["timeinfo"],
        State=b["state"],
        Images=images_base64
    )
    return bottle_info


@app.post("/bottles/approve/{id}")
async def approve_bottle(id: int):
    b = Bottle(conn=sqllite3.conn_bottle)
    await b.add_approved_bottle(id)
    return {"status": "approved"}


@app.post("/bottles/refuse/{id}")
async def refuse_bottle(id: int):
    b = Bottle(conn=sqllite3.conn_bottle)
    await b.refuse_bottle(id)
    return {"status": "refused"}


@app.get("/comments", response_class=HTMLResponse)
async def review_comments(request: Request):
    conn = sqllite3.conn_bottle
    bottle = Bottle(conn)
    comment = await bottle.get_random_comment_with_state_zero()
    if not comment:
        return templates.TemplateResponse("comments.html", {"request": request, "comment": None})
    return templates.TemplateResponse("comments.html", {"request": request, "comment": comment})


@app.get("/comments/random")
async def get_random_comment():
    conn = sqllite3.conn_bottle
    bottle = Bottle(conn)
    comment = await bottle.get_random_comment_with_state_zero()
    if not comment:
        raise HTTPException(status_code=404, detail="No comments found")
    return comment


@app.post("/comments/approve/{comment_id}")
async def approve_comment(comment_id: int):
    conn = sqllite3.conn_bottle
    bottle = Bottle(conn)
    success = await bottle.pass_comment_state(comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"status": "approved"}


@app.post("/comments/refuse/{comment_id}")
async def refuse_comment(comment_id: int):
    bottle = Bottle(sqllite3.conn_bottle)
    success = await bottle.refuse_comment_state(comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"status": "refused"}


@driver.on_startup
def _():
    logger.info('成功加载 web')


class NotSupportMessage(Exception):
    def __init__(self, message):
        super().__init__(message)

    def __str__(self) -> str:
        return super().__str__()






async def store_image_data(image_id: int, image_data: bytes, conn: Connection):
    """
    存储图像数据到数据库。
    :param image_id: 图像对应的 ID
    :param image_data: 图像的二进制数据
    :param conn: 数据库连接
    """
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO images (id, data) VALUES (?, ?)",
        (image_id, image_data)  # 直接存储传入的 image_id
    )
    conn.commit()

async def cache_file(msg: Message, image_id: int, conn: Connection):
    """
    缓存消息中的图片数据到数据库，最多只缓存两张图片。
    :param msg: 消息对象
    :param image_id: 图像对应的 ID
    :param conn: 数据库连接
    """
    semaphore = asyncio.Semaphore(2)  # 控制并发任务数量
    async with httpx.AsyncClient() as client:
        tasks = [
            cache_image_url(seg, client, image_id, conn, semaphore)
            for i, seg in enumerate(msg)
            if seg.type == "image" and i < 3  # 限制只处理前两张图片
        ]
        await asyncio.gather(*tasks)

async def cache_image_url(seg: MessageSegment, client: httpx.AsyncClient, image_id: int, conn: Connection, semaphore: asyncio.Semaphore):
    """
    缓存单个图片 URL 到数据库。
    :param seg: 包含图片 URL 的消息段
    :param client: HTTP 客户端
    :param image_id: 图像对应的 ID
    :param conn: 数据库连接
    :param semaphore: 控制并发任务数量的信号量
    """
    async with semaphore:
        url = seg.data.get("url")
        if not url:
            return

        seg.type = "cached_image"
        seg.data.clear()
        try:
            r = await client.get(url)
            data = r.content
        except httpx.TimeoutException:
            return

        if r.status_code != 200 or not data:
            return
        await store_image_data(image_id, data, conn)
        # 设置文件名时使用原始的 image_id
        seg.data = {"file": f"image_{image_id}"}

class Bottle:
    def __init__(self, conn):
        self.conn = conn

    async def get_random_comment_with_state_zero(self):
        """
        随机获取一个 state 为 0 的评论并返回它的详情
        """
        conn = self.conn
        cursor = conn.cursor()

        # 获取所有 state 为 0 的评论
        cursor.execute("SELECT * FROM comments WHERE state = 0")
        comments = cursor.fetchall()

        if not comments:
            return None

        # 随机选择一个评论
        random_comment = random.choice(comments)

        # 返回随机评论的详情
        return {
            "comment_id": random_comment[0],
            "bottle_id": random_comment[1],
            "content": random_comment[2],
            "state": random_comment[3],
            "uid": random_comment[4]
        }

    async def get_comments(self, id):
        """
        获取 comments 表中所有 id 对应的记录，且 state 为 200，
        并将结果以 'uid: content' 的格式返回，每条记录之间用换行符分隔。
        """
        # 创建一个异步 Cursor 对象
        cursor = self.conn.cursor()
        # SQL 查询语句
        query = "SELECT uid, content FROM comments WHERE id = ? AND state = 200"

        # 执行查询
        cursor.execute(query, (id,))

        # 获取所有查询结果
        rows = cursor.fetchall()

        # 如果找到了记录，则按指定格式组合结果
        if rows:
            formatted_results = "\n".join([f"{row[0]}: {row[1]}" for row in rows])
            return formatted_results
        else:
            return ""

    async def pass_comment_state(self, comment_id):
        """
        更新评论状态 200
        """
        conn = self.conn
        cursor = conn.cursor()

        # 检查 comments 表中是否存在给定的 comment_id
        cursor.execute("SELECT COUNT(*) FROM comments WHERE comment_id = ?", (comment_id,))
        count = cursor.fetchone()[0]
        if count == 0:
            return False

        # 更新 comments 表中对应记录的 state
        cursor.execute("UPDATE comments SET state = ? WHERE comment_id = ?", (200, comment_id))

        # 提交事务
        conn.commit()
        return True

    async def refuse_comment_state(self, comment_id):
        """
        更新评论状态 100
        """
        conn = self.conn
        cursor = conn.cursor()

        # 检查 comments 表中是否存在给定的 comment_id
        cursor.execute("SELECT COUNT(*) FROM comments WHERE comment_id = ?", (comment_id,))
        count = cursor.fetchone()[0]
        if count == 0:
            return False

        # 更新 comments 表中对应记录的 state
        cursor.execute("UPDATE comments SET state = ? WHERE comment_id = ?", (100, comment_id))

        # 提交事务
        conn.commit()
        return True

    async def find_all_pass_comments(self, bottle_id):
        """
        查找所有状态为 200 的评论（即已通过审核的评论）
        """
        conn = self.conn
        cursor = conn.cursor()

        # 查找所有状态为 200 的评论
        cursor.execute("SELECT * FROM comments WHERE id = ? AND state = 200", (bottle_id,))
        comments = cursor.fetchall()

        # 如果没有找到任何评论，返回空列表
        if not comments:
            return []

        # 返回评论的详情列表
        return [{
            "comment_id": comment[0],
            "bottle_id": comment[1],
            "content": comment[2],
            "state": comment[3],
            "uid": comment[4]
        } for comment in comments]

    async def add_comment_if_approved(self, bottle_id, text, uid):
        """
        评论瓶子
        """
        conn = self.conn
        cursor = conn.cursor()

        # 检查 approved 表中是否存在 bottle_id
        cursor.execute("SELECT COUNT(*) FROM approved WHERE id = ?", (bottle_id,))
        count = cursor.fetchone()[0]
        if count == 0:
            return False

        # 获取当前最大的 comment_id
        cursor.execute("SELECT MAX(comment_id) FROM comments")
        max_comment_id = cursor.fetchone()[0]
        if max_comment_id is None:
            max_comment_id = 0
        new_comment_id = max_comment_id + 1

        # 向 comments 表中添加评论
        cursor.execute("INSERT INTO comments (comment_id, id, content, state, uid) VALUES (?, ?, ?, ?, ?)",
                       (new_comment_id, bottle_id, text, 0, uid))

        # 提交事务
        conn.commit()
        return True

    async def get_approved_bottle_by_id(self, bottle_id):
        """
        根据给定的ID获取一个已过审的瓶子
        """

        # 查询特定行
        select_sql = """
        SELECT id, content, userid, groupid, timeinfo
        FROM approved
        WHERE id = ?
        """
        result = self.conn.execute(select_sql, (bottle_id,))
        row = result.fetchone()

        print(f"Row fetched: {row}")  # 调试信息

        if row:
            id, content, userid, groupid, timeinfo = row
            return {
                "id": id,
                "content": content,
                "userid": userid,
                "groupid": groupid,
                "timeinfo": timeinfo
            }
        else:
            return None

    async def random_get_approves_bottle(self):
        """
        随机获取一个已过审的瓶子
        """

        # 获取表中的行数
        row_count_sql = "SELECT COUNT(*) FROM approved"
        row_count = self.conn.execute(row_count_sql)
        row_count = (row_count.fetchone())[0]
        print(f"Total rows in approved table: {row_count}")  # 调试信息

        if row_count == 0:
            return None

        # 生成随机索引
        random_index = random.randint(0, row_count - 1)
        print(f"Random index generated: {random_index}")  # 调试信息

        # 查询特定行
        select_sql = f"""
        SELECT id, content, userid, groupid, timeinfo
        FROM approved
        LIMIT 1 OFFSET {random_index}
        """
        result = self.conn.execute(select_sql)
        row = result.fetchone()

        print(f"Row fetched: {row}")  # 调试信息

        if row:
            id, content, userid, groupid, timeinfo = row
            return {
                "id": id,
                "content": content,
                "userid": userid,
                "groupid": groupid,
                "timeinfo": timeinfo
            }
        else:
            return None

    async def fetch_bottles(self, id):
        """
        异步查询某个漂流瓶。
        """
        # 定义从 pending 表中获取数据的 SQL 语句
        select_query = """
        SELECT id, content, userid, groupid, timeinfo
        FROM pending
        WHERE id = ?;
        """
        # 执行查询
        cursor = self.conn.cursor()
        cursor.execute(select_query, (int(id),))
        result = cursor.fetchone()
        return result

    async def add_pending_bottle(self, id, message, userid, groupid, timeinfo):
        """
        异步增加待审核的漂流瓶。
        """

        data = {
            "id": int(id),
            "user_id": str(userid),
            "group_id": str(groupid),
            "content": message,
            "time": str(timeinfo),
            "state": 0
        }
        sql = """
        INSERT INTO pending (id, content, userid, groupid, timeinfo, state)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(sql,
                          (data["id"], data["content"], data["user_id"], data["group_id"], data["time"], data["state"]))
        self.conn.commit()
        return True

    async def refuse_bottle(self, id):
        """
        异步拒绝待审核的漂流瓶，并将相关图片数据设置为 None。
        """
        # 连接到数据库
        conn = self.conn
        cursor = conn.cursor()

        # 定义更新 pending 表状态的 SQL 语句
        update_pending_query = """
        UPDATE pending
        SET state = ?
        WHERE id = ?;
        """
        id_to_find = int(id)  # 替换为实际的 id 值

        # 更新 pending 表的状态
        new_state = 100
        cursor.execute(update_pending_query, (new_state, id_to_find))

        # 定义更新 images 表数据的 SQL 语句
        update_images_query = """
        UPDATE images
        SET data = NULL
        WHERE id = ?;
        """

        # 更新 images 表中的数据
        cursor.execute(update_images_query, (id_to_find,))

        # 提交更改
        conn.commit()

        return True

    async def add_approved_bottle(self, id):
        """
        异步增加已通过审核的漂流瓶。
        """

        # 连接到数据库
        conn = self.conn
        cursor = conn.cursor()

        # 定义从 pending 表中获取数据的 SQL 语句
        select_query = """
        SELECT id, content, userid, groupid, timeinfo
        FROM pending
        WHERE id = ?;
        """

        # 定义将数据插入 approved 表的 SQL 语句
        insert_query = """
        INSERT INTO approved (id, content, userid, groupid, timeinfo,up)
        VALUES (?, ?, ?, ?, ?, 0);
        """

        # 定义更新 pending 表状态的 SQL 语句
        update_query = """
        UPDATE pending
        SET state = ?
        WHERE id = ?;
        """

        # 假设 id 是要查询的具体值
        id_to_find = int(id)  # 替换为实际的 id 值

        try:
            # 执行查询
            cursor.execute(select_query, (id_to_find,))
            result = cursor.fetchone()

            if result:
                # 如果找到了记录，则插入到 approved 表
                cursor.execute(insert_query, result)

                # 更新 pending 表的状态
                new_state = 200
                cursor.execute(update_query, (new_state, id_to_find))

                # 提交事务
                conn.commit()
                print("Data inserted and state updated successfully.")
            else:
                print("No data found for the given ID.")

        except Exception as e:
            print(f"An error occurred: {e}")
            conn.rollback()

    async def up_bottle(self, bottle_id, uid):
        """
        点赞某个瓶子
        """
        conn = self.conn
        cursor = conn.cursor()

        # 初始化 ids_list 为空列表
        ids_list = []

        # 检查 user_up 表中 uid 对应的列表是否存在 bottle_id
        cursor.execute("SELECT ids FROM user_up WHERE uid = ?", (uid,))
        row = cursor.fetchone()
        if row:
            ids_list = row[0].split(",") if row[0] else []

        if str(bottle_id) in ids_list:
            return False, None

        # 确保 bottle_id 存在于 approved 表中
        cursor.execute("SELECT COUNT(*) FROM approved WHERE id = ?", (bottle_id,))
        if cursor.fetchone()[0] == 0:
            return False, None  # Bottle ID does not exist

        # 确保 up 列有默认值
        cursor.execute("SELECT up FROM approved WHERE id = ?", (bottle_id,))
        current_up_value = cursor.fetchone()[0]

        if current_up_value is None:
            current_up_value = 0

        # 修改 approved 表中 bottle_id 对应的 up 值 +1
        cursor.execute("UPDATE approved SET up = ? WHERE id = ?", (current_up_value + 1, bottle_id))

        # 提交事务
        conn.commit()

        # 获取更新后的 up 值
        cursor.execute("SELECT up FROM approved WHERE id = ?", (bottle_id,))
        new_up_value = cursor.fetchone()[0]

        if new_up_value is None:
            return False, None  # Failed to get updated value

        # 更新 user_up 表中 uid 对应的列表，添加 bottle_id
        ids_list.append(str(bottle_id))
        updated_ids = ",".join(ids_list)
        cursor.execute("INSERT OR REPLACE INTO user_up (uid, ids) VALUES (?, ?)", (uid, updated_ids))

        # 提交事务
        conn.commit()

        return True, new_up_value

    async def random_get_bottle(self):
        """
        随机获取一个待审的瓶子（state 等于 0）
        """

        # 获取表中 state 等于 0 的行数
        row_count_sql = "SELECT COUNT(*) FROM pending WHERE state = 0"
        row_count = self.conn.execute(row_count_sql)
        row_count = (row_count.fetchone())[0]
        print(f"Total rows in pending table with state 0: {row_count}")  # 调试信息
        if row_count == 0:
            return None

        # 生成随机索引
        random_index = random.randint(0, row_count - 1)
        print(f"Random index generated: {random_index}")  # 调试信息

        # 查询特定行
        select_sql = f"""
        SELECT id, content, userid, groupid, timeinfo, state
        FROM pending
        WHERE state = 0
        LIMIT 1 OFFSET {random_index}
        """
        result = self.conn.execute(select_sql)
        row = result.fetchone()

        print(f"Row fetched: {row}")  # 调试信息

        if row:
            id, content, userid, groupid, timeinfo, state = row
            return {
                "id": id,
                "content": content,
                "userid": userid,
                "groupid": groupid,
                "timeinfo": timeinfo,
                "state": state
            }
        else:
            return None

    async def get_bottle_images(self, id):
        """
        获取图片
        """

        # 创建一个 Cursor 对象
        conn = self.conn
        cursor = conn.cursor()

        # SQL 查询语句
        query = "SELECT data FROM images WHERE id = ?"

        # 执行查询
        cursor.execute(query, (id,))

        # 获取所有查询结果
        rows = cursor.fetchall()

        # 关闭 Cursor 和连接
        cursor.close()

        # 如果找到了记录，则返回 Blob 数据作为字节列表
        if rows:
            return [row[0] for row in rows]
        else:
            return []


async def id_add():
    async with aiofiles.open("./data/bottle_id.txt", "r+", encoding="utf_8") as f:
        k = int(await f.read()) + 1
        await f.close()
    async with aiofiles.open("./data/bottle_id.txt", "w+", encoding="utf_8") as b:
        await b.write(str(k))
        await b.close()
    return k


async def extract_and_join_text_from_message(message_list: list) -> str:
    """
    从消息列表中提取所有类型为 'text' 的消息段中的文本内容，并将它们合并成一个字符串。

    参数:
    message_list (list): 包含 MessageSegment 的列表。

    返回:
    str: 合并后的文本字符串。
    """
    texts = []
    for segment in message_list:
        if segment['type'] == 'text':
            texts.append(segment['data']['text'])
    return ''.join(texts)


async def serialize_message(message: Message, id, conn) -> List[Dict[str, Any]]:
    for seg in message:
        if seg.type not in ("text", "image"):
            raise NotSupportMessage("漂流瓶只支持文字和图片~")

    await cache_file(msg=message, image_id=id, conn=conn)
    return [seg.__dict__ for seg in message]


throw = on_command("丢瓶子", aliases={"扔瓶子"}, priority=5, block=True)
get_bottle = on_fullmatch("捡瓶子", priority=5, block=True)
up_bottle = on_command("点赞漂流瓶", priority=5, block=True)
comment = on_command("评论漂流瓶", priority=5, block=True)
read_bottle = on_command("查看漂流瓶", priority=5, block=True)


@read_bottle.handle()
async def _(bot: Bot, event: GroupMessageEvent, foo: Message = CommandArg()):
    try:
        a = int(foo.extract_plain_text())
    except:
        await read_bottle.finish("请输入正确的漂流瓶id")
    bottle = Bottle(sqllite3.conn_bottle)
    b = await bottle.get_approved_bottle_by_id(a)
    if b == None:
        cursor = sqllite3.conn_bottle.cursor()
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

    # 创建消息段
    message = Message(
        f"捡到漂流瓶id：{b['id']}\n"
        f"内容：{b['content']}\n"
        f"发送者：{b['userid']}\n"
        f"发送群：{b['groupid']}\n"
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
                j = await bot.call_api("get_group_member_info", **{
                    'group_id': event.group_id,
                    'user_id': int(user_id)
                })

                # 获取成员的名片或姓名
                name = j.get('card', j.get('nickname', '未知昵称'))

                # 输出结果
                print(f"{name}: {comment}")
            except Exception as e:
                # 如果 API 调用失败，则使用默认昵称
                print(f"未知昵称: {comment}")

    message += comments
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
    bottle = Bottle(sqllite3.conn_bottle)
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
    bottle = Bottle(sqllite3.conn_bottle)
    a, num = await bottle.up_bottle(foo, event.user_id)
    if not a:
        await up_bottle.finish("点赞失败，漂流瓶不存在或你已经点赞过了")
    else:
        await up_bottle.finish(f"点赞成功,现在有{num}个赞！")


@get_bottle.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    await get_bottle.send("捡瓶子中...")
    bottle = Bottle(sqllite3.conn_bottle)
    bottle_data = await bottle.random_get_approves_bottle()
    if not bottle_data:
        await get_bottle.finish("捞瓶子失败，没有漂流瓶~")
    img_bytes_list = await bottle.get_bottle_images(bottle_data['id'])

    # 创建消息段
    message = Message(
        f"捡到漂流瓶id：{bottle_data['id']}\n"
        f"内容：{bottle_data['content']}\n"
        f"发送者：{bottle_data['userid']}\n"
        f"发送群：{bottle_data['groupid']}\n"
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

    # 处理每条评论
    for line in comment_lines:
        # 分割每条评论以获取 ID 和消息
        id_and_comment = line.split(': ')
        if len(id_and_comment) == 2:
            user_id, comment = id_and_comment[0], ': '.join(id_and_comment[1:])

            try:
                # 调用 API 获取用户信息
                j = await bot.call_api("get_group_member_info", **{
                    'group_id': event.group_id,
                    'user_id': int(user_id)
                })

                # 获取成员的名片或姓名
                name = j.get('card', j.get('nickname', '未知昵称'))

                # 输出结果
                print(f"{name}: {comment}")
            except Exception as e:
                # 如果 API 调用失败，则使用默认昵称
                print(f"未知昵称: {comment}")

    message += comments
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
        if number_contains > 9:
            await throw.finish("丢瓶子内容过长，请不要超过9行哦~")
        id = await id_add()
        id = int(id)
        conn = sqllite3.conn_bottle
        ms = event.get_message()
        content = await serialize_message(ms, id, conn)
        bottle = Bottle(conn)
        time_info = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        a = await bottle.add_pending_bottle(id, foo, event.user_id, event.group_id, time_info)
        if a:
            await throw.finish(f"丢瓶子成功，请等待管理员审核~、id:{id}")
