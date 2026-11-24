from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from apps.api.app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
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
