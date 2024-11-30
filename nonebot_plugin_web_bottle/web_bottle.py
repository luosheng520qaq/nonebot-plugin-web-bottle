import asyncio
import base64
from argon2 import PasswordHasher
import random
from http import HTTPStatus
from pathlib import Path
from sqlite3 import Connection
from typing import Any, Literal

from io import BytesIO
from PIL import Image

import aiofiles
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from nonebot import get_app, get_driver, require
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.log import logger
from pydantic import BaseModel
from starlette.templating import _TemplateResponse

from . import data_deal
from .config import max_bottle_pic,bottle_account,bottle_password
from fastapi import Depends, FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_302_FOUND
from pydantic import BaseModel
from pathlib import Path
import secrets
import base64

require("nonebot_plugin_localstore")

import nonebot_plugin_localstore as store  # noqa: E402

app = get_app()

if not isinstance(app, FastAPI):
    msg = "本插件需要 FastAPI 驱动器才能正常运行"
    raise RuntimeError(msg)  # noqa: TRY004

driver = get_driver()

# 添加会话中间件
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

# 定义账号和密码
account = bottle_account
password = bottle_password
ph = PasswordHasher()
password_hash = ph.hash(password)

security = HTTPBasic()

# 获取当前文件所在目录
plugin_dir = Path(__file__).parent

# 设置静态文件目录路径
static_dir = plugin_dir / "templates" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 设置模板文件目录路径
templates_dir = plugin_dir / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


class BottleInfo(BaseModel):
    ID: int
    Content: str
    UserID: int
    GroupID: int
    TimeInfo: str
    State: int
    Images: list[str]


# 登录依赖项
def login_required(request: Request):
    if 'user' not in request.session:
        raise HTTPException(status_code=401, detail="请访问/login页面登陆后操作")


login_static_dir = plugin_dir / "templates" / "login" / "static"
app.mount("/login/static", StaticFiles(directory=str(login_static_dir)), name="login-static")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login/login.html", {"request": request})


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...), request: Request = None):
    print(password == password_sha256)
    if username == account and password == password_sha256:
        request.session['user'] = username
        return RedirectResponse(url="/check", status_code=HTTP_302_FOUND)
    raise HTTPException(status_code=401, detail="登录失败")


@app.get("/check", response_class=HTMLResponse)
async def read_item(request: Request, user: str = Depends(login_required)) -> _TemplateResponse:
    bottle = Bottle(conn=data_deal.conn_bottle)
    pending_count = await bottle.get_pending_count()
    return templates.TemplateResponse("index.html", {"request": request, "pending_count": pending_count})


@app.get("/bottles/random", response_model=BottleInfo)
async def get_random_bottle(user: str = Depends(login_required)) -> BottleInfo:
    bottle = Bottle(conn=data_deal.conn_bottle)
    b = await bottle.random_get_bottle()
    if not b:
        raise HTTPException(status_code=404, detail="No bottles found")

    images = await bottle.get_bottle_images(b["id"])
    images_base64 = [base64.b64encode(img).decode("utf-8") for img in images]

    return BottleInfo(
        ID=b["id"],
        Content=b["content"],
        UserID=b["userid"],
        GroupID=b["groupid"],
        TimeInfo=b["timeinfo"],
        State=b["state"],
        Images=images_base64,
    )


@app.post("/bottles/approve/{id}")
async def approve_bottle(id: int, user: str = Depends(login_required)) -> dict[str, str]:
    b = Bottle(conn=data_deal.conn_bottle)
    await b.add_approved_bottle(id)
    return {"status": "approved"}


@app.post("/bottles/refuse/{id}")
async def refuse_bottle(id: int, user: str = Depends(login_required)) -> dict[str, str]:
    b = Bottle(conn=data_deal.conn_bottle)
    await b.refuse_bottle(id)
    return {"status": "refused"}


@app.get("/comments", response_class=HTMLResponse)
async def review_comments(request: Request, user: str = Depends(login_required)) -> _TemplateResponse:
    conn = data_deal.conn_bottle
    bottle = Bottle(conn)
    comment = await bottle.get_random_comment_with_state_zero()
    if not comment:
        return templates.TemplateResponse("comments.html", {"request": request, "comment": None})
    return templates.TemplateResponse("comments.html", {"request": request, "comment": comment})


@app.get("/comments/random")
async def get_random_comment(user: str = Depends(login_required)) -> dict[str, Any]:
    conn = data_deal.conn_bottle
    bottle = Bottle(conn)
    comment = await bottle.get_random_comment_with_state_zero()
    if not comment:
        raise HTTPException(status_code=404, detail="No comments found")
    return comment


@app.post("/comments/approve/{comment_id}")
async def approve_comment(comment_id: int, user: str = Depends(login_required)) -> dict[str, str]:
    conn = data_deal.conn_bottle
    bottle = Bottle(conn)
    success = await bottle.pass_comment_state(comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"status": "approved"}


@app.post("/comments/refuse/{comment_id}")
async def refuse_comment(comment_id: int, user: str = Depends(login_required)) -> dict[str, str]:
    bottle = Bottle(data_deal.conn_bottle)
    success = await bottle.refuse_comment_state(comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"status": "refused"}


@driver.on_startup
def _():
    logger.info("成功加载 web")


class NotSupportMessageError(Exception):
    def __init__(self, *args: object):
        super().__init__(*args)

    def __str__(self) -> str:
        return super().__str__()


async def store_image_data(image_id: int, image_data: bytes, conn: Connection) -> None:
    """
    存储图像数据到数据库，使用有损压缩减小文件大小。
    :param image_id: 图像对应的 ID
    :param image_data: 图像的二进制数据
    :param conn: 数据库连接
    """
    # 将二进制数据转换为Image对象
    image = Image.open(BytesIO(image_data))

    # 创建一个BytesIO对象用于保存压缩后的图像数据
    output = BytesIO()

    # 保存图像时应用有损压缩
    # 对于JPEG图像，可以调整quality参数来控制压缩级别
    # quality参数范围为1（最差）到95（最好），通常推荐值为75-85
    format = image.format
    if format in ['JPEG', 'JPG']:
        image.save(output, format='JPEG', quality=75)  # 调整quality值以平衡质量和大小
    else:
        # 对于其他格式，如果支持，也尝试进行有损压缩
        # 这里假设所有支持的格式都支持有损压缩
        image.save(output, format=format, quality=75)

    # 获取压缩后的二进制数据
    compressed_image_data = output.getvalue()

    # 清理资源
    output.close()

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO images (id, data) VALUES (?, ?)",
        (image_id, compressed_image_data),  # 存储压缩后的图像数据
    )
    conn.commit()


async def cache_file(msg: Message, image_id: int, conn: Connection) -> None:
    """
    缓存消息中的图片数据到数据库，最多只缓存两张图片。
    :param msg: 消息对象
    :param image_id: 图像对应的 ID
    :param conn: 数据库连接
    """
    semaphore = asyncio.Semaphore(2)  # 控制并发任务数量
    max_number = max_bottle_pic
    async with httpx.AsyncClient() as client:
        tasks = [
            cache_image_url(seg, client, image_id, conn, semaphore)
            for i, seg in enumerate(msg)
            if seg.type == "image" and i <= max_number  # 限制只处理前两张图片
        ]
        await asyncio.gather(*tasks)


async def cache_image_url(
        seg: MessageSegment,
        client: httpx.AsyncClient,
        image_id: int,
        conn: Connection,
        semaphore: asyncio.Semaphore,
) -> None:
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

        if r.status_code != HTTPStatus.OK or not data:
            return
        await store_image_data(image_id, data, conn)
        # 设置文件名时使用原始的 image_id
        seg.data = {"file": f"image_{image_id}"}


class Bottle:
    def __init__(self, conn: Connection):
        self.conn = conn

    async def get_random_comment_with_state_zero(self) -> None | dict[str, Any]:
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
        random_comment = random.choice(comments)  # noqa: S311

        # 返回随机评论的详情
        return {
            "comment_id": random_comment[0],
            "bottle_id": random_comment[1],
            "content": random_comment[2],
            "state": random_comment[3],
            "uid": random_comment[4],
        }

    async def get_comments(self, id: int) -> str:
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
            return "\n".join([f"{row[0]}: {row[1]}" for row in rows])
        return ""

    async def pass_comment_state(self, comment_id: int) -> bool:
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

    async def refuse_comment_state(self, comment_id: int) -> bool:
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

    async def find_all_pass_comments(self, bottle_id: int) -> list[dict[str, Any]]:
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
        return [
            {
                "comment_id": comment[0],
                "bottle_id": comment[1],
                "content": comment[2],
                "state": comment[3],
                "uid": comment[4],
            }
            for comment in comments
        ]

    async def add_comment_if_approved(self, bottle_id: int, text: str, uid: str) -> bool:
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
        cursor.execute(
            "INSERT INTO comments (comment_id, id, content, state, uid) VALUES (?, ?, ?, ?, ?)",
            (new_comment_id, bottle_id, text, 0, uid),
        )

        # 提交事务
        conn.commit()
        return True

    async def get_approved_bottle_by_id(self, bottle_id: int) -> dict[str, Any] | None:
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

        logger.debug(f"Row fetched: {row}")  # 调试信息

        if row:
            id, content, userid, groupid, timeinfo = row
            return {
                "id": id,
                "content": content,
                "userid": userid,
                "groupid": groupid,
                "timeinfo": timeinfo,
            }
        return None

    async def random_get_approves_bottle(self) -> None | dict[str, Any]:
        """
        随机获取一个已过审的瓶子
        """

        # 获取表中的行数
        row_count_sql = "SELECT COUNT(*) FROM approved"
        row_count = self.conn.execute(row_count_sql)
        row_count = (row_count.fetchone())[0]
        logger.debug(f"Total rows in approved table: {row_count}")  # 调试信息

        if row_count == 0:
            return None

        # 生成随机索引
        random_index = random.randint(0, row_count - 1)  # noqa: S311
        logger.debug(f"Random index generated: {random_index}")  # 调试信息

        # 查询特定行
        select_sql = """
        SELECT id, content, userid, groupid, timeinfo
        FROM approved
        LIMIT 1 OFFSET ?
        """
        result = self.conn.execute(select_sql, (random_index,))
        row = result.fetchone()

        logger.debug(f"Row fetched: {row}")  # 调试信息

        if row:
            id, content, userid, groupid, timeinfo = row
            return {
                "id": id,
                "content": content,
                "userid": userid,
                "groupid": groupid,
                "timeinfo": timeinfo,
            }
        return None

    async def fetch_bottles(self, id: int) -> Any:  # noqa: ANN401
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
        return cursor.fetchone()

    async def add_pending_bottle(
            self, id: int, message: str, userid: str, groupid: str, timeinfo: str
    ) -> Literal[True]:
        """
        异步增加待审核的漂流瓶。
        """

        data = {
            "id": int(id),
            "user_id": str(userid),
            "group_id": str(groupid),
            "content": message,
            "time": str(timeinfo),
            "state": 0,
        }
        sql = """
        INSERT INTO pending (id, content, userid, groupid, timeinfo, state)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(
            sql,
            (
                data["id"],
                data["content"],
                data["user_id"],
                data["group_id"],
                data["time"],
                data["state"],
            ),
        )
        self.conn.commit()
        return True

    async def refuse_bottle(self, id: int) -> Literal[True]:
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

        # 更新 pending 表的状态
        new_state = 100
        cursor.execute(update_pending_query, (new_state, id))

        # 定义更新 images 表数据的 SQL 语句
        update_images_query = """
        UPDATE images
        SET data = NULL
        WHERE id = ?;
        """

        # 更新 images 表中的数据
        cursor.execute(update_images_query, (id,))

        # 提交更改
        conn.commit()

        return True

    async def add_approved_bottle(self, id: int) -> None:
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

        try:
            # 执行查询
            cursor.execute(select_query, (id,))
            result = cursor.fetchone()

            if result:
                # 如果找到了记录，则插入到 approved 表
                cursor.execute(insert_query, result)

                # 更新 pending 表的状态
                new_state = 200
                cursor.execute(update_query, (new_state, id))

                # 提交事务
                conn.commit()
                logger.debug("Data inserted and state updated successfully.")
            else:
                logger.debug("No data found for the given ID.")

        except Exception as e:  # noqa: BLE001
            logger.error("An error occurred: ")
            logger.exception(e)
            conn.rollback()

    async def up_bottle(self, bottle_id: int, uid: str) -> tuple[Literal[False], None] | tuple[Literal[True], Any]:
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
        cursor.execute(
            "INSERT OR REPLACE INTO user_up (uid, ids) VALUES (?, ?)",
            (uid, updated_ids),
        )

        # 提交事务
        conn.commit()

        return True, new_up_value

    async def random_get_bottle(self) -> None | dict[str, Any]:
        """
        随机获取一个待审的瓶子（state 等于 0）
        """

        # 获取表中 state 等于 0 的行数
        row_count_sql = "SELECT COUNT(*) FROM pending WHERE state = 0"
        row_count = self.conn.execute(row_count_sql)
        row_count = (row_count.fetchone())[0]
        logger.debug(f"Total rows in pending table with state 0: {row_count}")  # 调试信息
        if row_count == 0:
            return None

        # 生成随机索引
        random_index = random.randint(0, row_count - 1)  # noqa: S311
        logger.debug(f"Random index generated: {random_index}")  # 调试信息

        # 查询特定行
        select_sql = """
        SELECT id, content, userid, groupid, timeinfo, state
        FROM pending
        WHERE state = 0
        LIMIT 1 OFFSET ?
        """
        result = self.conn.execute(select_sql, (random_index,))
        row = result.fetchone()

        logger.debug(f"Row fetched: {row}")  # 调试信息

        if row:
            id, content, userid, groupid, timeinfo, state = row
            return {
                "id": id,
                "content": content,
                "userid": userid,
                "groupid": groupid,
                "timeinfo": timeinfo,
                "state": state,
            }
        return None

    async def get_pending_count(self) -> int:
        """
        获取剩余待审核的瓶子数量
        """

        # 获取表中 state 等于 0 的行数
        count_sql = "SELECT COUNT(*) FROM pending WHERE state = 0"
        count_result = self.conn.execute(count_sql)
        count = (count_result.fetchone())[0]
        logger.debug(f"Total pending bottles with state 0: {count}")  # 调试信息

        return count

    async def get_bottle_images(self, id: int) -> list[bytes]:
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
        return []


plugin_data = store.get_data_dir("nonebot_plugin_web_bottle")
file_path = plugin_data / "bottle_id.txt"


async def id_add() -> int:
    # Ensure the directory exists
    plugin_data.mkdir(exist_ok=True)

    # Check if the file exists, if not, create it with an initial value of 0
    if not file_path.exists():
        async with aiofiles.open(file_path, "w+", encoding="utf_8") as f:
            await f.write("0")
            await f.close()

    # Read the current ID, increment, and write back the new value
    async with aiofiles.open(file_path, "r+", encoding="utf_8") as f:
        k = int(await f.read()) + 1
        await f.close()

    async with aiofiles.open(file_path, "w+", encoding="utf_8") as b:
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
    return "".join(segment["data"]["text"] for segment in message_list if segment["type"] == "text")


async def serialize_message(message: Message, id: int, conn: Connection) -> list[dict[str, Any]]:
    for seg in message:
        if seg.type not in ("text", "image"):
            msg = "漂流瓶只支持文字和图片~"
            raise NotSupportMessageError(msg)

    await cache_file(msg=message, image_id=id, conn=conn)
    return [seg.__dict__ for seg in message]