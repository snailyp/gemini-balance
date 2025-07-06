import asyncio
from app.database.connection import database, connect_to_db, disconnect_from_db
from app.database.models import Settings as SettingsModel
from sqlalchemy import select

async def read_settings():
    await connect_to_db()
    try:
        query = select(SettingsModel.key, SettingsModel.value).where(
            SettingsModel.key.in_(['GEMINI_BASE_URL', 'GEMINI_BASE_URL_SELECTION_STRATEGY', 'LOG_LEVEL'])
        )
        results = await database.fetch_all(query)
        for row in results:
            print(f"Key: {row.key}, Value: {row.value}")
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(read_settings())