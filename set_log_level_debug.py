
import asyncio
from app.database.connection import database, connect_to_db, disconnect_from_db
from app.database.models import Settings as SettingsModel
from sqlalchemy import update

async def set_log_level_debug():
    await connect_to_db()
    try:
        await database.execute(
            update(SettingsModel)
            .where(SettingsModel.key == 'LOG_LEVEL')
            .values(value='DEBUG')
        )
        print("Set LOG_LEVEL to DEBUG in database.")
    finally:
        await disconnect_to_db()

if __name__ == "__main__":
    asyncio.run(set_log_level_debug())
