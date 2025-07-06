"""
Bulk Verify Keys Script

This script is designed to be run in a Docker environment to bulk-verify all active API keys.
It connects to the database, fetches all active keys, and sends a test request to the Gemini API
to validate each key. Keys that fail validation (e.g., return a 403 error) will be automatically
deactivated in the database.

How to run in Docker:
1. Make sure your Docker container is running:
   docker-compose up -d

2. Execute this script inside the running container:
   docker-compose exec gemini-balance python bulk_verify_keys.py
"""
import asyncio
import sys
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load .env file before importing app configurations
load_dotenv()

# The script is run from /app in the Docker container, which is added to PYTHONPATH.
# No need to manually modify sys.path.
from app.config.config import settings, sync_initial_settings
from app.database.connection import connect_to_db, disconnect_from_db
from app.database.initialization import create_tables, import_env_to_settings
from app.service.key.key_manager import get_key_manager_instance, KeyManager
from app.service.chat.gemini_chat_service import GeminiChatService
from app.domain.gemini_models import GeminiContent, GeminiRequest
from app.log.logger import Logger

logger = Logger.setup_logger("bulk_verify_keys")

async def bulk_verify_gemini_keys():
    """
    Main function to perform bulk verification of Gemini API keys.
    """
    logger.info("=========================================")
    logger.info("  Starting Bulk API Key Verification     ")
    logger.info("=========================================")

    try:
        # 1. Connect to the database
        await connect_to_db()
        logger.info("Database connected successfully.")
        
        # Import database-dependent services after connection is established
        from app.database.services import api_key_service 

        # 2. Initialize database and sync settings
        # This ensures the script can run independently.
        create_tables()
        import_env_to_settings()
        await api_key_service.sync_keys_from_config()
        await sync_initial_settings()
        logger.info("Database initialized and settings synchronized.")

        # 3. Get KeyManager and GeminiChatService instances
        key_manager: KeyManager = await get_key_manager_instance()
        chat_service = GeminiChatService(key_manager)

        # 4. Get all active API keys
        all_keys_data = await api_key_service.get_active_keys('gemini')
        active_keys = [key_data.key_value for key_data in all_keys_data]
        
        if not active_keys:
            logger.info("No active API keys found to verify.")
            return

        logger.info(f"Found {len(active_keys)} active API keys to verify.")

        # 5. Prepare a dummy request for verification
        gemini_request = GeminiRequest(
            contents=[
                GeminiContent(
                    role="user",
                    parts=[{"text": "hi"}],
                )
            ],
            generation_config={"temperature": 0.7, "top_p": 1.0, "max_output_tokens": 10}
        )

        # 6. Define a verification task for a single key
        async def verify_single_key(api_key: str) -> Dict[str, Any]:
            try:
                logger.debug(f"Verifying key ending in ...{api_key[-4:]}")
                # The generate_content method handles 403 errors and deactivates keys
                await chat_service.generate_content(
                    settings.TEST_MODEL,
                    gemini_request,
                    api_key
                )
                logger.info(f"Key ending in ...{api_key[-4:]} is VALID.")
                return {"key": api_key, "status": "valid"}
            except Exception as e:
                # Error is logged and key deactivated by chat_service
                logger.warning(f"Key ending in ...{api_key[-4:]} is INVALID. Error: {e}")
                return {"key": api_key, "status": "invalid", "error": str(e)}

        # 7. Run verification tasks concurrently
        tasks = [verify_single_key(key) for key in active_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 8. Report results
        valid_count = 0
        invalid_count = 0
        
        # Re-fetch keys to get updated status
        updated_keys_data = await api_key_service.get_active_keys('gemini')
        updated_active_keys = {key.key_value for key in updated_keys_data}
        deactivated_count = 0

        for key in active_keys:
            is_valid_in_run = any(r.get("key") == key and r.get("status") == "valid" for r in results if isinstance(r, dict))

            if is_valid_in_run:
                valid_count += 1
            else:
                invalid_count += 1
                if key not in updated_active_keys:
                    deactivated_count += 1

        logger.info("--- Bulk Verification Summary ---")
        logger.info(f"Total keys processed: {len(active_keys)}")
        logger.info(f"Valid keys: {valid_count}")
        logger.info(f"Invalid keys (failed verification): {invalid_count}")
        logger.info(f"Keys automatically deactivated: {deactivated_count}")
        logger.info("-------------------------------")

    except Exception as e:
        logger.critical(f"An unhandled error occurred during bulk verification: {e}", exc_info=True)
    finally:
        # 9. Disconnect from the database
        await disconnect_from_db()
        logger.info("Database disconnected.")
        logger.info("=========================================")
        logger.info("  Bulk Verification Finished           ")
        logger.info("=========================================")

if __name__ == "__main__":
    # Ensure the script is run with the app's root in the Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Now we can import app modules
    from app.config.config import settings, sync_initial_settings
    from app.database.connection import connect_to_db, disconnect_from_db
    from app.database.initialization import create_tables, import_env_to_settings
    from app.service.key.key_manager import get_key_manager_instance, KeyManager
    from app.service.chat.gemini_chat_service import GeminiChatService
    from app.domain.gemini_models import GeminiContent, GeminiRequest
    from app.log.logger import Logger

    logger = Logger.setup_logger("bulk_verify_keys")
    
    asyncio.run(bulk_verify_gemini_keys())
