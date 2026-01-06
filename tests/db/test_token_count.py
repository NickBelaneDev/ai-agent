import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.service import ChatSessionDBService
from src.db.models import ChatSession

@pytest.mark.asyncio
async def test_token_count_increment(db_session: AsyncSession):
    """
    Test that token count is incremented correctly using atomic updates.
    """
    service = ChatSessionDBService(db_session)
    user_name = "token_tester"
    
    # 1. Create a session
    session = await service.create_session(user_name)
    await service.commit()
    session_id = session.session_id
    
    # Initial check
    assert session.token_count == 0
    
    # 2. Update with some tokens (normal increment)
    await service.update_session(session, [], token_usage=100, reset_token_count=False)
    await service.commit()
    
    # Refresh to see DB state
    await db_session.refresh(session)
    assert session.token_count == 100
    
    # 3. Update again (increment)
    await service.update_session(session, [], token_usage=50, reset_token_count=False)
    await service.commit()
    
    await db_session.refresh(session)
    assert session.token_count == 150

@pytest.mark.asyncio
async def test_token_count_reset(db_session: AsyncSession):
    """
    Test that token count is reset correctly when requested.
    """
    service = ChatSessionDBService(db_session)
    user_name = "reset_tester"
    
    # 1. Create session with initial tokens
    session = await service.create_session(user_name)
    session.token_count = 500 # Manually set for setup
    await service.commit()
    
    # 2. Perform a reset update (e.g. new conversation start)
    # Even if we used 10 tokens in this new turn, the total should be reset to just those 10
    await service.update_session(session, [], token_usage=10, reset_token_count=True)
    await service.commit()
    
    await db_session.refresh(session)
    assert session.token_count == 10

@pytest.mark.asyncio
async def test_token_count_race_condition_simulation(db_session: AsyncSession):
    """
    Simulates a race condition where two updates happen 'simultaneously'.
    Since we use atomic updates in the service, the DB should handle this correctly
    by summing them up, rather than one overwriting the other.
    """
    service = ChatSessionDBService(db_session)
    user_name = "race_tester"
    session = await service.create_session(user_name)
    await service.commit()
    
    # We need two separate service instances/transactions to simulate concurrency properly
    # but within this test setup, we can verify the atomic SQL generation logic 
    # by calling update_session twice without refreshing the object in between.
    
    # Update 1: +100 tokens
    await service.update_session(session, [], token_usage=100, reset_token_count=False)
    
    # Update 2: +200 tokens (without refreshing session.token_count from DB)
    # If it were python-side logic: session.token_count (0) + 200 = 200.
    # With atomic DB update: token_count = token_count + 200.
    await service.update_session(session, [], token_usage=200, reset_token_count=False)
    
    await service.commit()
    await db_session.refresh(session)
    
    # Should be 300 (100 + 200), not 200 or 100.
    assert session.token_count == 300
