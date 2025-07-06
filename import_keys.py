import asyncio
from app.database.connection import database
from app.database.models import APIKey
from sqlalchemy import insert, select
import os

async def import_keys_from_file(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    with open(file_path, 'r') as f:
        keys = [line.strip() for line in f if line.strip()]

    if not keys:
        print("No keys found in the file.")
        return

    print(f"Found {len(keys)} keys in {file_path}. Starting import...")

    await database.connect()
    try:
        # Fetch existing keys to avoid duplicates
        existing_keys_query = select(APIKey.key_value)
        existing_keys_result = await database.fetch_all(existing_keys_query)
        existing_keys = {row["key_value"] for row in existing_keys_result}
        print(f"Found {len(existing_keys)} existing keys in the database.")

        keys_to_insert = []
        for key in keys:
            if key not in existing_keys:
                keys_to_insert.append({
                    "key_value": key,
                    "service": "gemini",
                    "status": "active"
                })
        
        if not keys_to_insert:
            print("All keys from file already exist in the database. No new keys to insert.")
            return

        print(f"Inserting {len(keys_to_insert)} new keys...")
        
        # Bulk insert
        async with database.transaction():
            insert_query = insert(APIKey).values(keys_to_insert)
            await database.execute(insert_query)
        
        print(f"Successfully imported {len(keys_to_insert)} keys into the database.")

    except Exception as e:
        print(f"An error occurred during key import: {e}")
    finally:
        await database.disconnect()

if __name__ == "__main__":
    keys_file = "/app/allkeys.txt"
    asyncio.run(import_keys_from_file(keys_file))
