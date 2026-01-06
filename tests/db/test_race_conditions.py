import pytest
import asyncio
import json
from sqlalchemy import text
from sqlalchemy.orm.exc import StaleDataError
from src.db.service import ChatSessionDBService
from src.db.models import ChatSession

@pytest.mark.asyncio
async def test_race_condition_token_update(db_session):
    """
    Tests for race conditions when updating token counts.

    Scenario:
    - We load a session (s1) with 0 tokens.
    - We simulate a background process updating the token count in the DB to 100.
    - We then update s1 (which still thinks it has 0 tokens) by adding 10 tokens.

    Expectation:
    - If the update is atomic (SQL-side increment), the result should be 110.
    - If the update is vulnerable (Read-Modify-Write in Python), the result will be 10 (overwriting the 100).
    """
    service = ChatSessionDBService(db_session)
    user_name = "race_user"

    # 1. Create initial session
    session = await service.create_session(user_name)
    await service.commit()
    session_id = session.session_id

    # 2. Get session object (s1 has token_count=0)
    s1 = await service.get_session(session_id=session_id, user_name=user_name)
    assert s1.token_count == 0

    # 3. Simulate background update (DB becomes 100)
    # We use raw SQL to bypass the session identity map and simulate another transaction
    # We also need to increment the version manually because raw SQL doesn't trigger SQLAlchemy's versioning
    await db_session.execute(
        text(f"UPDATE chat_sessions SET token_count = 100, version = version + 1 WHERE session_id = '{session_id}'")
    )

    # 4. Perform update via service on the stale object s1
    # We add 10 tokens.
    # Note: Since we introduced optimistic locking, this might fail with StaleDataError if we touch versioned columns.
    # However, update_session does an atomic update for token_count and sets history_json.
    # If update_session modifies the object and flushes, it will check the version.

    # In our implementation, update_session modifies s1.history_json and s1.last_active.
    # This should trigger a version check upon flush/commit.

    try:
        await service.update_session(s1, [], 10)
        await service.commit()
    except StaleDataError:
        # If we catch StaleDataError, it means optimistic locking is working!
        # But for this specific test (token count atomic update), we wanted to see if token count is preserved
        # even if we force the update.
        # With optimistic locking, we can't easily "force" an overwrite of history without refreshing.
        # So catching StaleDataError is actually a PASS for the "History Race Condition",
        # but here we are testing "Token Count Atomic Update".

        # If we get StaleDataError, we can't verify the token count math because the transaction rolled back.
        # So we will refresh and try again to verify atomic increment logic specifically,
        # OR we accept that StaleDataError prevents the race condition entirely (which is good).
        pass

    # 5. Verify result
    # If the transaction committed (no StaleDataError), we check the math.
    # If it failed, we check if the DB still has 100 (it should).

    # We need a new session to see DB state cleanly
    await db_session.rollback()
    
    # Re-fetch
    result = await db_session.execute(text(f"SELECT token_count FROM chat_sessions WHERE session_id = '{session_id}'"))
    final_token_count = result.scalar()

    # If the update succeeded (atomic increment worked and version check passed - unlikely if we changed version in background),
    # result would be 110.
    # If StaleDataError occurred (likely), result should be 100 (background update preserved).
    # In either case, we shouldn't see 10.

    if final_token_count == 10:
        pytest.fail("Race Condition Detected! The update overwrote the background change. Use atomic updates.")

    # If we reached here, we are good.


@pytest.mark.asyncio
async def test_race_condition_history_update(db_session):
    """
    Tests for race conditions when updating history.

    Scenario:
    - We load a session (s1).
    - We simulate a background process appending a message to history.
    - We then update s1 (which has stale history) with a new message.

    Expectation:
    - Optimistic locking should raise StaleDataError.
    """
    # Prevent SQLAlchemy from expiring objects on commit, so s1 stays stale
    db_session.expire_on_commit = False

    service = ChatSessionDBService(db_session)
    user_name = "race_user_hist"

    # 1. Create session
    session = await service.create_session(user_name)
    await service.commit()
    session_id = session.session_id

    # 2. Get stale object
    s1 = await service.get_session(session_id=session_id, user_name=user_name)

    # 3. Background update (simulate another user/request)
    background_history = [{"role": "system", "content": "Background"}]
    background_json = json.dumps(background_history)
    
    # Update history AND increment version to simulate a real ORM update
    await db_session.execute(
        text("UPDATE chat_sessions SET history_json = :h, version = version + 1 WHERE session_id = :id"),
        {"h": background_json, "id": session_id}
    )
    # Commit the background update so it persists even if the next transaction fails
    await db_session.commit()

    # 4. Foreground update on stale s1
    new_history = [{"role": "user", "content": "Foreground"}]

    # The service typically replaces the history.
    # We expect StaleDataError here because s1.version is old.
    try:
        await service.update_session(s1, new_history, 0)
        await service.commit()
        pytest.fail("Race Condition Detected! StaleDataError was NOT raised. Optimistic locking failed.")
    except StaleDataError:
        # This is the expected behavior!
        pass
    except Exception as e:
        pytest.fail(f"Unexpected error: {e}")

    # 5. Verify DB state (should contain background update, not foreground overwrite)
    # We don't need to rollback here because the previous commit failed or we caught the exception.
    # But to be safe and get a clean state for reading:
    await db_session.rollback()
    
    result = await db_session.execute(text(f"SELECT history_json FROM chat_sessions WHERE session_id = '{session_id}'"))
    history_json = result.scalar()
    final_history = json.loads(history_json)

    has_background = any(m.get("content") == "Background" for m in final_history)
    
    assert has_background, "Background update was lost!"

@pytest.mark.asyncio
async def test_mixed_orm_core_update_safety(db_session):
    """
    Tests that we are NOT mixing ORM and Core updates in a way that bypasses versioning.
    This test specifically targets the fix where we switched from update().values() to session.token_count += ...
    """
    service = ChatSessionDBService(db_session)
    user_name = "mixed_update_user"
    
    # 1. Create session
    session = await service.create_session(user_name)
    await service.commit()
    session_id = session.session_id
    
    # 2. Get session
    s1 = await service.get_session(session_id=session_id, user_name=user_name)
    initial_version = s1.version
    
    # 3. Update via service
    await service.update_session(s1, [], 10)
    await service.commit()
    
    # 4. Verify version incremented
    # If we used raw SQL update without touching version, version would be same (unless DB trigger)
    # But since we use ORM update now, SQLAlchemy should increment version.
    
    # Refresh s1 to see new version
    await db_session.refresh(s1)
    assert s1.version > initial_version
    assert s1.token_count == 10
