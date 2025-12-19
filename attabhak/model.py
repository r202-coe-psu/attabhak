"""Database models and engine setup using SQLModel and SQLite."""

from typing import Optional, AsyncGenerator
from datetime import datetime
from contextlib import asynccontextmanager
from sqlmodel import JSON, SQLModel, Field, create_engine, Session, Column
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker as sessionmaker


class SensorData(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=datetime.now, index=True)

    class Config:
        arbitrary_types_allowed = True


# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./data/attabhak.db"
engine = create_async_engine(DATABASE_URL)
# engine = create_async_engine(DATABASE_URL, echo=True)


async def create_db_and_tables():

    async with engine.begin() as conn:
        # run_sync is necessary as create_all is a synchronous operation
        await conn.run_sync(SQLModel.metadata.create_all)


AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False # Prevents automatic data refresh after a commit
)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

