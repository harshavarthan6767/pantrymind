import requests

payload = {
    "message": "What should I buy?",
    "session_id": "test_1",
    "user_id": "default_user"
}
print("Sending request...")
resp = requests.post("http://localhost:8000/api/agent/chat", data=payload, stream=True)
print("Response status:", resp.status_code)
for line in resp.iter_lines():
    print("LINE:", line)
