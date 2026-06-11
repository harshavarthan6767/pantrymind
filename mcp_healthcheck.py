#!/usr/bin/env python
"""
mcp_healthcheck.py — Phase 3 · Day 4
======================================
Verifies that the MongoDB MCP server can be started and responds correctly.
Run before demo or as part of CI.

Usage:
    .venv\\Scripts\\python mcp_healthcheck.py
"""
import asyncio
import os
import sys
import subprocess
import json
from dotenv import load_dotenv

load_dotenv()


async def check_mcp_server() -> bool:
    """
    Spawns the MongoDB MCP server process briefly and checks if it can list tools.
    Uses the same command as the ADK toolset.
    """
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DATABASE", "finmind")

    if not uri:
        print("❌ MONGODB_URI not set in .env")
        return False

    print(f"  Checking MongoDB MCP server (@mongodb-js/mcp-server-mongodb)...")
    print(f"  Database: {db_name}")

    # Minimal MCP initialization request
    init_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "healthcheck", "version": "1.0"}
        }
    }) + "\n"

    list_tools_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }) + "\n"

    try:
        proc = await asyncio.create_subprocess_exec(
            "npx", "@mongodb-js/mcp-server-mongodb",
            "--connectionString", uri,
            "--database", db_name,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Send init + list tools
        proc.stdin.write(init_request.encode())
        proc.stdin.write(list_tools_request.encode())
        await proc.stdin.drain()

        # Read response lines (with timeout)
        tools_found = []
        try:
            for _ in range(10):  # Read up to 10 lines
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
                if not line:
                    break
                line_str = line.decode().strip()
                if line_str:
                    try:
                        data = json.loads(line_str)
                        if "result" in data and "tools" in data.get("result", {}):
                            tools_found = [t["name"] for t in data["result"]["tools"]]
                    except json.JSONDecodeError:
                        pass
        except asyncio.TimeoutError:
            pass

        proc.terminate()
        await proc.wait()

        if tools_found:
            print(f"  ✅ MCP server started and returned {len(tools_found)} tools:")
            for t in tools_found[:10]:
                print(f"     • {t}")
            return True
        else:
            print("  ⚠️  MCP server started but no tools returned (check connection)")
            return False

    except FileNotFoundError:
        print("  ❌ npx not found — ensure Node.js is installed")
        return False
    except Exception as e:
        print(f"  ❌ MCP server check failed: {e}")
        return False


async def check_server_health() -> bool:
    """Check if the FastAPI server is up."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=3) as resp:
            data = json.loads(resp.read())
            status = data.get("status")
            db = data.get("database")
            print(f"  ✅ FastAPI server: {status} | DB: {db}")
            return True
    except Exception as e:
        print(f"  ❌ FastAPI server not reachable: {e}")
        return False


async def main():
    print("\n🔍 PantryMind MCP + Server Health Check")
    print("  " + "─" * 50)
    
    results = []
    
    # 1. Check FastAPI server
    print("\n  [1/2] FastAPI Server")
    results.append(await check_server_health())
    
    # 2. Check MCP server
    print("\n  [2/2] MongoDB MCP Server")
    results.append(await check_mcp_server())

    print("\n  " + "─" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"  ✅ All {total} checks passed — system ready for demo\n")
        return 0
    else:
        print(f"  ⚠️  {passed}/{total} checks passed — fix issues before demo\n")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
