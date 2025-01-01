import sqlite3

from nonebot import get_driver, logger, require

require("nonebot_plugin_localstore")
from PIL import Image,UnidentifiedImageError
import nonebot_plugin_localstore as store  # noqa: E402
from io import BytesIO
drive = get_driver()
conn_bottle: sqlite3.Connection
plugin_data = store.get_data_dir("nonebot_plugin_web_bottle")

image_path = plugin_data / 'img'
image_path.mkdir(parents=True, exist_ok=True)

@drive.on_startup
def _():
    global conn_bottle  # noqa: PLW0603 # !WTF

    # 获取插件的数据目录
    plugin_data = store.get_data_dir("nonebot_plugin_web_bottle")
    logger.info(f"漂流瓶插件数据存储目录将会在：{plugin_data}")

    # 确保目录存在
    plugin_data.mkdir(exist_ok=True)

    # 数据库文件路径
    db_path = plugin_data / "bottle.db"
    logger.info("正在检查数据库是否存在！")

    # 检查数据库文件是否存在
    if not db_path.exists():
        logger.warning("数据库不存在，将跳过创建 images 表！")

        # 创建并连接到数据库（但不创建 images 表）
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        logger.info(f"尝试在路径 {db_path} 中建立表")

        # 执行多个 SQL 语句创建表
        cursor.execute("""
            CREATE TABLE approved (
                id INTEGER PRIMARY KEY,
                content TEXT,
                userid TEXT,
                groupid TEXT,
                timeinfo TEXT,
                up INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE comments (
                comment_id INTEGER PRIMARY KEY,
                id INTEGER,
                content TEXT,
                state TEXT,
                uid TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE pending (
                id INTEGER PRIMARY KEY,
                content TEXT,
                userid TEXT,
                groupid TEXT,
                timeinfo TEXT,
                state TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE user_up (
                uid INTEGER PRIMARY KEY UNIQUE,
                ids TEXT
            )
        """)

        # 提交更改并关闭连接
        conn.commit()
        conn.close()
        logger.success("数据库和表成功创建！")
    else:
        logger.info("数据库已存在，跳过创建步骤！")

        # 连接到数据库检查 images 表结构
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查 images 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='images'")
        images_table_exists = cursor.fetchone()

        if images_table_exists:
            logger.info("检测到 images 表，正在迁移数据，请稍候...")
            cursor.execute("SELECT id, data FROM images")
            rows = cursor.fetchall()

            # 在迁移数据的循环中添加校验
            for image_id, image_data in rows:
                if not image_data:
                    logger.warning(f"ID 为 {image_id} 的数据为空，跳过迁移！")
                    continue

                # 确保对应的 ID 文件夹存在
                target_dir = image_path / str(image_id)
                target_dir.mkdir(parents=True, exist_ok=True)

                try:
                    # 打开二进制数据为图像
                    image = Image.open(BytesIO(image_data))
                    # 将图片转换为 webp 格式
                    image = image.convert("RGB")  # 确保兼容性

                    # 找到子文件夹中最大索引值，生成下一个文件名
                    existing_files = list(target_dir.glob("*.webp"))
                    max_index = -1  # 初始为 -1，如果没有文件则从 0 开始
                    for file in existing_files:
                        try:
                            # 提取文件名中的数字索引（假设文件名格式为 image_<index>.webp）
                            index = int(file.stem.split('_')[-1])  # 提取 "image_<index>" 中的 <index>
                            max_index = max(max_index, index)
                        except ValueError:
                            continue  # 忽略无法解析为数字的文件名

                    next_index = max_index + 1  # 下一个文件名的索引
                    target_path = target_dir / f"image_{next_index}.webp"

                    # 保存图片
                    image.save(target_path, format="WEBP", quality=80)  # 调整质量以平衡大小
                    logger.info(f"成功迁移 ID 为 {image_id} 的图片至 {target_path}")
                except UnidentifiedImageError:
                    logger.error(f"ID 为 {image_id} 的数据不是有效图片，跳过迁移！")
                except Exception as e:
                    logger.error(f"迁移 ID 为 {image_id} 的图片时发生未知错误：{e}")

            logger.info("迁移完成，正在删除 images 表...")
            cursor.execute("DROP TABLE images")
            conn.commit()
            logger.success("images 表已删除，数据迁移成功！")

        conn.close()

    logger.success("加载成功！")

    # 创建全局数据库连接
    db_path = store.get_data_dir("nonebot_plugin_web_bottle") / "bottle.db"
    conn_bottle = sqlite3.connect(db_path, check_same_thread=False)
