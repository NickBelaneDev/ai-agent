import pytest
import uuid
from fastapi import HTTPException
from src.db.service import ChatSessionDBService
from src.db.models import ChatSession

@pytest.mark.asyncio
async def test_session_security_forbidden_access(db_session):
    """
    Testet, dass ein User nicht auf die Session eines anderen Users zugreifen kann.
    Szenario:
    1. User A erstellt eine Session.
    2. User A interagiert mit der Session (simuliert durch Update).
    3. User B versucht, auf die Session von User A zuzugreifen.
    4. Erwartetes Ergebnis: HTTPException 403 Forbidden.
    """
    service = ChatSessionDBService(db_session)
    
    # 1. User A erstellt eine Session
    user_a = "UserA"
    session_id = str(uuid.uuid4())
    
    # Session erstellen
    session_a = await service.create_session(user_name=user_a, session_id=session_id)
    await service.commit()
    
    # Verifizieren, dass Session existiert
    fetched_session = await service.get_session(session_id=session_id, user_name=user_a)
    assert fetched_session is not None
    assert fetched_session.user_name == user_a
    assert fetched_session.session_id == session_id

    # 2. User A "schreibt" etwas (Update Session)
    # Wir simulieren das Update, um sicherzugehen, dass die Session "lebt"
    history_mock = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]
    await service.update_session(fetched_session, history_data=history_mock, token_usage=10)
    await service.commit()

    # 3. User B versucht Zugriff auf die gleiche Session ID
    user_b = "UserB"
    
    # Wir müssen sicherstellen, dass User B existiert (optional, je nach Implementierung von get_session)
    # Aber get_session prüft nur die Session-Daten, User B muss nicht zwingend in der DB sein für den Check,
    # aber für saubere Tests legen wir ihn an.
    await service.get_or_create_user(user_b)
    await service.commit()

    # 4. Der Zugriff muss fehlschlagen
    print(f"\nTesting security: User {user_b} accessing Session {session_id} of {user_a}")

    with pytest.raises(HTTPException) as exc_info:
        await service.get_session(session_id=session_id, user_name=user_b)
    
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden"

    print("Security check passed: 403 Forbidden received.")
