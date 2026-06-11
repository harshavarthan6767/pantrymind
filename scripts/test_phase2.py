import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_expiry_scan():
    print("Testing /api/proactive/scan-expiry...")
    resp = requests.post(f"{BASE_URL}/api/proactive/scan-expiry")
    print(resp.status_code, resp.json())
    print()

def test_budget_scan():
    print("Testing /api/proactive/scan-budget...")
    resp = requests.post(f"{BASE_URL}/api/proactive/scan-budget")
    print(resp.status_code, resp.json())
    print()

def test_shopping_list():
    print("Testing Shopping List via Chat...")
    # Using the /api/agent/chat/stream endpoint (ADK)
    # The ADK uses streaming SSE, but we can also use /api/chat if it routes correctly?
    # Wait, /api/chat points to the old ChatService. /api/agent/chat/stream points to ADK runner!
    # Let's hit the SSE endpoint.
    headers = {"Content-Type": "application/json"}
    payload = {
        "message": "I need to go grocery shopping. What should I buy? Check the budget too.",
        "session_id": "test_session_123",
        "user_id": "default_user"
    }
    resp = requests.post(f"{BASE_URL}/api/agent/chat", data=payload, stream=True)
    for line in resp.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith("data: "):
                try:
                    event = json.loads(decoded[6:])
                    if event["type"] == "token":
                        print(event["data"], end="", flush=True)
                    elif event["type"] == "agent":
                        print(f"\n[AGENT TRANSFER] {event['data']}")
                    elif event["type"] == "tool_call":
                        print(f"\n[TOOL CALL] {event['data']}")
                except Exception as e:
                    pass
    print("\n")


if __name__ == "__main__":
    test_expiry_scan()
    test_budget_scan()
    test_shopping_list()
