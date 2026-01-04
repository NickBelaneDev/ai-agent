import pytest
from sqlalchemy import select, text
from src.db.service import ChatSessionDBService
from src.db.models import User, ChatSession
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_sql_injection_user_name(db_session):
    """
    Tests if SQL injection via user_name is possible.
    SQLAlchemy should bind parameters and treat the string literally.
    """
    service = ChatSessionDBService(db_session)
    
    # A classic SQL injection attempt
    # Goal would be to manipulate the WHERE clause, e.g., WHERE name = '' OR '1'='1'
    injection_payload = "' OR '1'='1"
    
    # We create a user with this name.
    # If injection is prevented, the user will be named exactly this string.
    user = await service.get_or_create_user(injection_payload)
    await service.commit()
    
    # Check 1: The name must match the payload exactly
    assert user.name == injection_payload
    
    # Check 2: We look directly into the DB to see if we get "all" users or just the one
    # First, we create a "normal" user.
    normal_user = await service.get_or_create_user("normal_user")
    await service.commit()
    
    # If we search for the injection user now, we must NOT find the normal user.
    # We use SQLAlchemy select directly here, as done in the service.
    stmt = select(User).where(User.name == injection_payload)
    result = await db_session.execute(stmt)
    users = result.scalars().all()
    
    assert len(users) == 1
    assert users[0].name == injection_payload
    assert users[0].name != "normal_user"

@pytest.mark.asyncio
async def test_sql_injection_session_id(db_session):
    """
    Tests SQL injection via session_id during retrieval.
    """
    service = ChatSessionDBService(db_session)
    
    # Preparation: Create a legitimate session
    legit_user = "legit_user"
    legit_session = await service.create_session(legit_user)
    await service.commit()
    
    # Injection attempt during retrieval
    # We try to get the legitimate session by manipulating the ID
    # Assuming the query is: SELECT * FROM sessions WHERE session_id = '{input}'
    # Input: ' OR '1'='1
    injection_id = "' OR '1'='1"

    # The service should search for a session that has EXACTLY this ID.
    # Since no such session exists, it should return None (or raise 404).
    # It must definitely NOT return the legit_session.

    # Note: get_session raises 404 if ID is provided but not found.
    with pytest.raises(HTTPException) as exc_info:
        await service.get_session(session_id=injection_id)
    
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_raw_sql_execution_safety(db_session):
    """
    An additional test demonstrating that even when using parameters directly
    in text() clauses (if one were to use them), binding must be used.
    This is more of a test of SQLAlchemy configuration/usage.
    """
    # We insert a user
    user_name = "safe_user"
    db_session.add(User(name=user_name))
    await db_session.commit()

    # Unsafe way (DO NOT USE IN CODE, ONLY TO DEMO WHAT WOULD HAPPEN):
    # await db_session.execute(text(f"SELECT * FROM users WHERE name = '{injection_payload}'"))

    # Safe way with binding (as SQLAlchemy ORM does internally):
    injection_payload = "' OR '1'='1"
    stmt = text("SELECT * FROM users WHERE name = :name")
    result = await db_session.execute(stmt, {"name": injection_payload})
    found_users = result.fetchall()
    
    # Should be empty, as there is no user with the name "' OR '1'='1"
    assert len(found_users) == 0
    
    # Counter-check: Search for the real user
    result = await db_session.execute(stmt, {"name": user_name})
    found_users = result.fetchall()
    assert len(found_users) == 1

@pytest.mark.asyncio
async def test_advanced_sql_injection_drop_table(db_session):
    """
    A 'harder' test: Attempt to delete a table (DROP TABLE).
    This simulates a destructive attack.
    """
    service = ChatSessionDBService(db_session)
    
    # Payload: Attempts to terminate the current query and append a DROP TABLE query.
    # In SQLite, multi-statement execution is often disabled or restricted by default,
    # but we test here if the string is interpreted as code at all.
    # Payload: '; DROP TABLE users; --
    destructive_payload = "'; DROP TABLE users; --"
    
    # We try to use this payload as user_name.
    # If injection works, the users table would be deleted.
    await service.get_or_create_user(destructive_payload)
    await service.commit()
    
    # Verification: Does the users table still exist?
    # We try to insert/retrieve a normal user.
    # If the table were gone, this would raise an OperationalError.
    try:
        normal_user = await service.get_or_create_user("survivor_user")
        await service.commit()
        assert normal_user.name == "survivor_user"
    except Exception as e:
        pytest.fail(f"Database integrity compromised or table dropped: {e}")

    # Verification 2: The destructive payload should simply exist as a strange name.
    stmt = select(User).where(User.name == destructive_payload)
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    
    assert user is not None
    assert user.name == destructive_payload

@pytest.mark.asyncio
async def test_advanced_sql_injection_union_attack(db_session):
    """
    Another 'hard' test: UNION BASED Injection.
    Attempt to read data from another table (sqlite_master).
    """
    service = ChatSessionDBService(db_session)
    
    # Payload: Attempts to append results from sqlite_master to the user list.
    # Goal: ' UNION SELECT name, null FROM sqlite_master --
    # Note: Column count must match, User has 'name' (String).
    union_payload = "' UNION SELECT name FROM sqlite_master --"

    # We use get_or_create_user.
    # Query is approx: SELECT ... FROM users WHERE name = :name
    # If injection works: SELECT ... FROM users WHERE name = '' UNION SELECT name FROM sqlite_master --'

    # We expect that a user with this cryptic name is simply created.
    user = await service.get_or_create_user(union_payload)
    await service.commit()
    
    assert user.name == union_payload
    
    # We check if we really only get this one user and no system table names
    stmt = select(User).where(User.name == union_payload)
    result = await db_session.execute(stmt)
    users = result.scalars().all()
    
    # If injection were successful, multiple "users" (which are table names) could return here,
    # or there would be syntax errors.
    # Since SQLAlchemy binds, we search exactly for the string.
    assert len(users) == 1
    assert users[0].name == union_payload
