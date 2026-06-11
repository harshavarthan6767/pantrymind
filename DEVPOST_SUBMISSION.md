# PantryMind - Devpost Submission

## Project Name
PantryMind

## Tagline
AI-powered multi-agent life management with voice, governance, and real-time inventory intelligence

## Description
PantryMind is an intelligent household management application built to automate receipt scanning, inventory tracking, and meal planning. Instead of relying on a single monolithic LLM, PantryMind uses a **Multi-Agent Architecture** powered by Google ADK (Agent Development Kit), Gemini 2.5 Flash, and the official MongoDB MCP server. It brings together financial tracking, dietary preferences, and pantry management under one natural language interface.

We also prioritize **Governance and Safety**. The system separates "read-only" agents from "governed write" agents. Whenever an agent attempts to modify your core inventory, a **Human-in-the-Loop policy engine** intercepts the action, assesses the risk level, and presents an approval prompt to the user before executing the database transaction.

## How we built it
- **Orchestration**: Google ADK routes user queries to specialized agents (Pantry, Kitchen, Finance, Shopping, Voice).
- **LLM**: Gemini 2.5 Flash and Gemini Live (for seamless voice interactions).
- **Database**: MongoDB Atlas with Vector Search for semantic queries ("What ingredients do I have for a Thai curry?").
- **Integration**: The official `@mongodb-js/mcp-server-mongodb` running via `npx` handles all database interactions.
- **Frontend**: Vite + React, offering a unified dashboard with an interactive trace timeline to observe agent reasoning.
- **Backend**: FastAPI with async Motor.

## Challenges we ran into
Integrating the official MongoDB MCP Server required mapping complex schema structures and ensuring that agent-generated tool calls were perfectly formatted for the MCP protocol. Another major challenge was Voice UI latency — we had to implement a "safety net" to capture dual-signals (audio transcript + structured output) to reliably trigger agent handoffs when the user spoke complex commands.

## Accomplishments that we're proud of
- Successfully integrating the **official MongoDB MCP server** without any middleman wrappers.
- Building a robust **Human-in-the-Loop approval system** that intercepts potentially destructive actions.
- Implementing **Reflexion** in our Kitchen Chef agent, allowing it to double-check its own meal plans against dietary constraints and expiring inventory before presenting them to the user.

## What we learned
We learned the power of separating concerns among AI agents. By isolating the Finance agent from the Pantry agent, we improved accuracy and reduced hallucination. We also realized how critical an approval layer is for AI agents interacting with real-world databases — granting an AI autonomous write access requires guardrails.

## What's next for PantryMind
- Integrating supermarket APIs to automatically order missing ingredients.
- Expanding the dietary constraint engine to support highly personalized medical diets.
- Adding a mobile companion app for easier on-the-go receipt scanning.

## Built With
- google-adk
- gemini-2.5-flash
- mongodb-atlas
- mcp
- fastapi
- react
- vite
- electron
