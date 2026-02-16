import os
import asyncpg
from typing import Optional


class Database:
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            db_url = os.getenv("DB_URL")
            if not db_url:
                raise ValueError("DB_URL environment variable is not set")
            
            # 따옴표가 포함되어 있을 경우 제거 (실수로 들어간 경우 대비)
            db_url = db_url.strip('"').strip("'")
            
            # DBCP 설정
            cls._pool = await asyncpg.create_pool(
                dsn=db_url,
                min_size=1,
                max_size=10
            )
        return cls._pool

    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
