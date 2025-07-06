
import asyncio
from app.database.services import api_key_service
from app.database.connection import connect_to_db, disconnect_from_db

async def main():
    await connect_to_db()
    # 注意：这里我们使用一个示例密钥，因为它存在于 .env.example 中
    # 并且很可能已经被脚本同步到了数据库中。
    # 如果这个密钥不存在，这个操作不会产生任何效果。
    key_to_ban = "AIzaSyxxxxxxxxxxxxxxxxxxx"
    print(f"Attempting to ban key: {key_to_ban}")
    success = await api_key_service.update_key_status(key_to_ban, 'banned')
    if success:
        print(f"Successfully updated status for key: {key_to_ban}")
    else:
        print(f"Could not update status for key: {key_to_ban}. It might not exist in the database.")
    await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(main())
