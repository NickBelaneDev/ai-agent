import asyncio
import sys
from sqlalchemy import select
from src.db.connection import AsyncSessionLocal
from src.db.models import User, ChatSession

async def inspect_database():
    """
    Connects to the database and prints all Users and ChatSessions.
    Useful for quick debugging and verification.
    """
    print("--- Inspecting Database ---")
    
    async with AsyncSessionLocal() as session:
        # 1. Inspect Users
        print("\n[Users]")
        result_users = await session.execute(select(User))
        users = result_users.scalars().all()
        
        if not users:
            print("  No users found.")
        else:
            for user in users:
                print(f"  - Name: {user.name}")

        # 2. Inspect Chat Sessions
        print("\n[Chat Sessions]")
        result_sessions = await session.execute(select(ChatSession))
        chat_sessions = result_sessions.scalars().all()
        
        if not chat_sessions:
            print("  No chat sessions found.")
        else:
            for cs in chat_sessions:
                print(f"  - Session ID: {cs.session_id}")
                print(f"    User:       {cs.user_name}")
                print(f"    Tokens:     {cs.token_count}")
                print(f"    Last Active:{cs.last_active}")
                print(f"    History Len:{len(cs.history_json) if cs.history_json else 0} chars")
                print("    ---")

    print("\n--- Inspection Complete ---")

if __name__ == "__main__":
    # Windows-specific fix for asyncio loop policy if needed, 
    # though usually not strictly required for simple scripts unless using specific event loops.
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(inspect_database())
