"""统一管理异步 SQLite checkpoint 连接的生命周期。"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


def checkpoint_path(path=None):
    root = Path(__file__).resolve().parents[2]
    selected = Path(path or os.getenv('LEADGRAPH_CHECKPOINT_DB') or root/'data/checkpoints.sqlite3')
    return selected if selected.is_absolute() else root/selected


@asynccontextmanager
async def open_checkpointer(path=None):
    selected = checkpoint_path(path)
    selected.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(selected)) as saver:
        await saver.setup()
        yield saver
