from apps.api.app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency que fornece uma sessão de banco de dados assíncrona.
    A sessão é fechada automaticamente ao final da requisição.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
