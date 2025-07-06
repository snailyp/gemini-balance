import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import update
from app.database.connection import connect_to_db, disconnect_from_db, database, engine # Import database and engine
from app.database.models import APIKey
from app.log.logger import Logger

logger = Logger.setup_logger("reset_key_status")

async def reset_all_api_keys_status():
    """
    Resets the status of all API keys to 'active' and sets failure_count to 0.
    """
    logger.info("=========================================")
    logger.info("  Starting API Key Status Reset          ")
    logger.info("=========================================")

    try:
        # Load .env file before connecting to the database
        load_dotenv()

        # Connect to the database
        await connect_to_db()
        logger.info("Database connected successfully.")

        # Update all API keys using the 'database' object
        stmt = (
            update(APIKey.__table__)
            .values(status="active", failure_count=0)
        )
        result = await database.execute(stmt)
            
        logger.info(f"Successfully reset status for {result} API keys.")

    except Exception as e:
        logger.critical(f"An unhandled error occurred during key status reset: {e}", exc_info=True)
    finally:
        # Disconnect from the database
        await disconnect_from_db()
        logger.info("Database disconnected.")
        logger.info("=========================================")
        logger.info("  API Key Status Reset Finished        ")
        logger.info("=========================================")

if __name__ == "__main__":
    # Ensure the script is run with the app's root in the Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    asyncio.run(reset_all_api_keys_status())