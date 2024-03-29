import os

from sqlalchemy import create_engine
from databases import Database
from functools import wraps

HOST = f'mysql://root:123456@{os.environ.get("DB_HOST", "127.0.0.1")}:3306/test_db'
engine = create_engine(HOST)
db = Database(HOST)


def connect(foo):
    @wraps(foo)
    async def decorate(*args, **kw):
        if not db.is_connected:
            await db.connect()
        return await foo(*args, **kw)
    return decorate
