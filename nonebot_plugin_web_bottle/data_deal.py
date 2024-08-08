import sqlite3
from nonebot import require
from nonebot import get_driver
import os
from nonebot import logger

require('nonebot_plugin_localstore')
import nonebot_plugin_localstore as store

drive = get_driver()


@drive.on_startup
def _():
    global conn_bottle
    # 获取插件的数据目录
    plugin_data = store.get_data_dir('nonebot_plugin_web_bottle')

    # 确保目录存在
    os.makedirs(plugin_data, exist_ok=True)

    # 数据库文件路径
    db_path = plugin_data / 'bottle.db'
    logger.info('正在检查数据库是否存在！')

    # 检查数据库文件是否存在
    if not db_path.exists():
        logger.error('数据库不存在，正在尝试创建！')
        # 创建并连接到数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        logger.info(f'尝试在路径 {db_path} 中建立表')

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
                id INTEGER PRIMARY KEY,
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
        logger.success('数据库和表成功创建！')
    else:
        logger.info('数据库已存在，跳过创建步骤！')
    logger.success('加载成功！')
    # 创建全局数据库连接
    db_path = store.get_data_dir('nonebot_plugin_web_bottle') / 'bottle.db'
    conn_bottle = sqlite3.connect(db_path, check_same_thread=False)
