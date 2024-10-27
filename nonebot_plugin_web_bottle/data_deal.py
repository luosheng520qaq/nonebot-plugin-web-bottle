import sqlite3

from nonebot import get_driver, logger, require

require("nonebot_plugin_localstore")

import nonebot_plugin_localstore as store  # noqa: E402

drive = get_driver()


@drive.on_startup
def _():
    global conn_bottle  # noqa: PLW0603 # !WTF
    # 获取插件的数据目录
    plugin_data = store.get_data_dir("nonebot_plugin_web_bottle")

    # 确保目录存在
    plugin_data.mkdir(exist_ok=True)

    # 数据库文件路径
    db_path = plugin_data / "bottle.db"
    logger.info("正在检查数据库是否存在！")

    # 检查数据库文件是否存在
    if not db_path.exists():
        logger.error("数据库不存在，正在尝试创建！")
        # 创建并连接到数据库
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
            CREATE TABLE images (
                id INTEGER,  -- 保留 id 列但不是主键
                data BLOB
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

        # 检查 images 表是否存在，并获取其结构
        cursor.execute("PRAGMA table_info(images)")
        columns = cursor.fetchall()

        # 检查 id 是否为主键
        is_id_primary_key = any(col[1] == 'id' and col[5] == 1 for col in columns)

        if is_id_primary_key:
            logger.info("images 表的 id 列为主键，正在去除主键约束！")
            # 创建一个新的表，复制原数据
            cursor.execute("""
                CREATE TABLE images_new (
                    id INTEGER,  -- 保留 id 列但不是主键
                    data BLOB
                )
            """)

            cursor.execute("INSERT INTO images_new (id, data) SELECT id, data FROM images")

            # 删除旧表
            cursor.execute("DROP TABLE images")
            # 重命名新表为原表名
            cursor.execute("ALTER TABLE images_new RENAME TO images")
            conn.commit()
            logger.success("images 表的主键约束已去除！")

        conn.close()

    logger.success("加载成功！")
    # 创建全局数据库连接
    db_path = store.get_data_dir("nonebot_plugin_web_bottle") / "bottle.db"
    conn_bottle = sqlite3.connect(db_path, check_same_thread=False)
