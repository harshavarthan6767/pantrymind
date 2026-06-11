# PantryMind Voice Agent Regression Test Plan

## Test 1 — No-Tools Voice Pipeline

Environment:

```env
VOICE_DEBUG=true
VOICE_DISABLE_TOOLS=true
```

Input:

```text
Hello PantryMind
```

Expected:

```text
Assistant says: I heard you clearly.
```

Expected logs:

```text
sent realtime input to Gemini
Gemini audio chunk received
sent audio chunk to frontend
```

***

## Test 2 — Root Agent Health

Endpoint:

```http
GET /api/voice/agent-health
```

Expected response:

```json
{
  "ok": true
}
```

Failure handling:

```text
If MongoDB or ADK fails, endpoint must return ok=false with a readable error.
```

***

## Test 3 — Tool Call Voice Flow

Environment:

```env
VOICE_DEBUG=true
VOICE_DISABLE_TOOLS=false
```

Input:

```text
Create a meal plan.
```

Expected logs:

```text
Gemini tool call: delegate_to_pantrymind
root_agent.run started
root_agent.run completed
Tool response sent to Gemini for function_call_id
Gemini audio chunk received
sent audio chunk to frontend
```

Expected UI:

```text
Listening... → Thinking... → Speaking... → Listening...
```

***

## Test 4 — Root Agent Timeout

Simulate slow `root_agent.run()`.

Expected:

```text
Voice assistant speaks graceful timeout message.
UI does not hang.
WebSocket remains alive.
```

***

## Test 5 — MongoDB Failure

Temporarily break MongoDB URI or block network.

Expected:

```text
root_agent.run error logged
Voice assistant speaks graceful error message
UI does not remain stuck on Listening...
```

***

## Test 6 — Frontend AudioContext

Expected browser console:

```text
Output AudioContext: running
Server message audio
Speaking...
```

Expected behavior:

```text
Audio plays without requiring a second click.
```
