import asyncio
from app.database.connection import database, connect_to_db, disconnect_from_db
from app.database.models import Settings as SettingsModel
from sqlalchemy import update
from app.core.constants import API_VERSION

async def reset_db_settings():
    await connect_to_db()
    try:
        # Reset GEMINI_BASE_URL
        await database.execute(
            update(SettingsModel)
            .where(SettingsModel.key == 'GEMINI_BASE_URL')
            .values(value=f'["https://generativelanguage.googleapis.com/{API_VERSION}"]')
        )
        print(f"Reset GEMINI_BASE_URL to [\"https://generativelanguage.googleapis.com/{API_VERSION}\"]")

        # Reset GEMINI_BASE_URL_SELECTION_STRATEGY
        await database.execute(
            update(SettingsModel)
            .where(SettingsModel.key == 'GEMINI_BASE_URL_SELECTION_STRATEGY')
            .values(value='round_robin')
        )
        print("Reset GEMINI_BASE_URL_SELECTION_STRATEGY to 'round_robin'")

    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(reset_db_settings())
