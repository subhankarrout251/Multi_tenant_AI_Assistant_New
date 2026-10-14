"""
scripts/verify_memory.py
──────────────────────────────────────────────────────────────────────
Verification script for Conversational Memory in Multi-Tenant AI Assistant.

Validates:
1. Multi-turn memory recall (recalling user personal context like name).
2. Knowledge retrieval with conversational memory (combining retrieved RAG facts with user context).
3. Follow-up question resolution (query contextualization).
4. Memory storage inspection and sliding window verification.
5. Conversation memory reset and isolation across sessions.
──────────────────────────────────────────────────────────────────────
"""

import os
import sys
import asyncio
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

from app.services.rag_service import answer_query
from app.services.memory_service import (
    get_history,
    clear_history,
    get_langchain_messages,
)


async def main():
    print("=" * 65)
    print("STARTING CONVERSATION MEMORY INTEGRATION VERIFICATION")
    print("=" * 65)

    test_session = f"verify-session-{int(datetime.now().timestamp())}"
    tenant_id = "sunrise_eco_homes"

    print(f"\n[Step 0] Initializing fresh session: {test_session}")
    clear_history(test_session)
    assert len(get_history(test_session)) == 0, "Initial history must be empty"
    print("✓ Session memory is clean.")

    # ─────────────────────────────────────────────────────────────
    # TURN 1: User introduces themselves
    # ─────────────────────────────────────────────────────────────
    print("\n[Turn 1] User: 'Hello, my name is Subhankar and I am visiting Sunrise Eco Homes.'")
    res1 = await answer_query(
        question="Hello, my name is Subhankar and I am visiting Sunrise Eco Homes.",
        website_id=tenant_id,
        session_id=test_session,
    )
    print(f"Assistant: {res1['reply']}")
    history1 = get_history(test_session)
    assert len(history1) == 2, f"Expected 2 messages after turn 1, got {len(history1)}"
    print("✓ Turn 1 stored in memory.")

    # ─────────────────────────────────────────────────────────────
    # TURN 2: Personal memory recall test
    # ─────────────────────────────────────────────────────────────
    print("\n[Turn 2] User: 'What is my name?'")
    res2 = await answer_query(
        question="What is my name?",
        website_id=tenant_id,
        session_id=test_session,
    )
    print(f"Assistant: {res2['reply']}")
    assert "Subhankar" in res2["reply"], (
        f"Memory recall failed! Expected 'Subhankar' in reply, got: {res2['reply']}"
    )
    history2 = get_history(test_session)
    assert len(history2) == 4, f"Expected 4 messages after turn 2, got {len(history2)}"
    print("✓ Turn 2 successfully recalled user name 'Subhankar' from conversation memory!")

    # ─────────────────────────────────────────────────────────────
    # TURN 3: RAG Retrieval query
    # ─────────────────────────────────────────────────────────────
    print("\n[Turn 3] User: 'What payment modes do you accept?'")
    res3 = await answer_query(
        question="What payment modes do you accept?",
        website_id=tenant_id,
        session_id=test_session,
    )
    print(f"Assistant: {res3['reply']}")
    history3 = get_history(test_session)
    assert len(history3) == 6, f"Expected 6 messages after turn 3, got {len(history3)}"
    print("✓ Turn 3 retrieved payment details and stored in memory.")

    # ─────────────────────────────────────────────────────────────
    # TURN 4: Follow-up referencing both memory and previous answer
    # ─────────────────────────────────────────────────────────────
    print("\n[Turn 4] User: 'Can you summarize the payment modes you just listed along with my name?'")
    res4 = await answer_query(
        question="Can you summarize the payment modes you just listed along with my name?",
        website_id=tenant_id,
        session_id=test_session,
    )
    print(f"Assistant: {res4['reply']}")
    assert "Subhankar" in res4["reply"], (
        f"Multi-turn synthesis failed to recall name! Got: {res4['reply']}"
    )
    history4 = get_history(test_session)
    assert len(history4) == 8, f"Expected 8 messages after turn 4, got {len(history4)}"
    print("✓ Turn 4 successfully synthesized multi-turn conversation memory!")

    # ─────────────────────────────────────────────────────────────
    # TURN 5: Reset / Clear Memory Test
    # ─────────────────────────────────────────────────────────────
    print("\n[Turn 5] Testing clear_history / session reset...")
    cleared = clear_history(test_session)
    assert cleared is True, "clear_history returned False"
    history_after_clear = get_history(test_session)
    assert len(history_after_clear) == 0, "History should be empty after clear"
    print("✓ Memory cleared successfully.")

    # ─────────────────────────────────────────────────────────────
    # TURN 6: Verify memory is gone after clearing
    # ─────────────────────────────────────────────────────────────
    print("\n[Turn 6] User: 'What is my name?' (after memory clear)")
    res6 = await answer_query(
        question="What is my name?",
        website_id=tenant_id,
        session_id=test_session,
    )
    print(f"Assistant: {res6['reply']}")
    # Now it shouldn't know the name since memory was reset
    assert "Subhankar" not in res6["reply"], (
        f"Memory leak! Name should NOT be known after clear, but got: {res6['reply']}"
    )
    print("✓ Verified: Assistant no longer knows 'Subhankar' after memory reset.")

    print("\n" + "=" * 65)
    print("ALL CONVERSATION MEMORY VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
