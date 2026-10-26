# -*- coding: utf-8 -*-
# File: services/puter_client.py
# Description: Puter.js / OpenRouter LLM client and Agno Model adapter.

import os
import sys
import re
import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Iterator
from pathlib import Path
from dotenv import load_dotenv

from agno.models.base import Model
from agno.models.response import ModelResponse

# Load environment configuration
_curr_path = Path(__file__).resolve()
_potential_env_paths = [
    _curr_path.parent / ".env",
    _curr_path.parent.parent / ".env",
    _curr_path.parent.parent.parent / ".env",
    _curr_path.parent.parent.parent.parent / ".env",
]
for env_path in _potential_env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
        break


def clean_and_parse_json_robust(raw_text: str) -> Dict[str, Any]:
    """Robustly strips code fences, <think> tags, C-style comments, and cleans trailing commas to parse JSON."""
    if not raw_text or not isinstance(raw_text, str):
        return {}

    cleaned = raw_text.strip()
    # Strip <think> tags from thinking models
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned, flags=re.IGNORECASE).strip()

    # Extract JSON inside markdown code blocks if present
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    # Remove inline comments like // and block comments /* */
    cleaned = re.sub(r'//[^\n\r]*', '', cleaned)
    cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)

    # Remove trailing commas before closing braces/brackets
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)

    # 1. Direct parse attempt
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 2. Extract outermost curly braces
    first_curly = cleaned.find('{')
    last_curly = cleaned.rfind('}')
    if first_curly != -1 and last_curly > first_curly:
        candidate = cleaned[first_curly:last_curly + 1]
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 3. Extract outermost square brackets
    first_brack = cleaned.find('[')
    last_brack = cleaned.rfind(']')
    if first_brack != -1 and last_brack > first_brack:
        candidate = cleaned[first_brack:last_brack + 1]
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        try:
            items = json.loads(candidate)
            if isinstance(items, list):
                return {"item_criteria": items}
        except Exception:
            pass

    return {}


class PuterLlmClient:
    """High-reliability client for Puter.js AI completion API."""

    def __init__(self, token: Optional[str] = None, model: Optional[str] = None):
        self.token = token or os.getenv("PUTER_AUTH_TOKEN", "")
        self.model = model or os.getenv("PUTER_MODEL", "openrouter:openrouter/free")
        self.url = "https://api.puter.com/drivers/call"

    def complete(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 45) -> str:
        """Executes a chat completion call with retry handling."""
        if not self.token or not str(self.token).strip():
            raise RuntimeError("PUTER_AUTH_TOKEN is missing or empty. Please login to Puter or set PUTER_AUTH_TOKEN.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "interface": "puter-chat-completion",
            "driver": "ai-chat",
            "test_mode": False,
            "method": "complete",
            "args": {
                "messages": messages,
                "model": self.model,
                "stream": False,
                "temperature": 0.1
            }
        }

        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST"
        )

        import socket
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            with urllib.request.urlopen(req, timeout=timeout) as res:
                data = json.loads(res.read().decode("utf-8"))
                if not data.get("success"):
                    raise RuntimeError(f"Puter API error: {data}")
                result = data.get("result", {})
                message = result.get("message", {})
                return message.get("content", "")
        except Exception as e:
            print(f"[PuterLlmClient] Error calling Puter API: {e}", file=sys.stderr)
            raise
        finally:
            socket.setdefaulttimeout(old_timeout)

        return ""

    def complete_json(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 45) -> Dict[str, Any]:
        """Executes complete and extracts parsed JSON."""
        raw_text = self.complete(prompt, system_prompt=system_prompt, timeout=timeout)
        return clean_and_parse_json_robust(raw_text)

    def test_connection(self) -> Dict[str, Any]:
        """Validates network connectivity and authentication against Puter API."""
        t0 = time.time()
        if not self.token:
            return {"success": False, "error": "PUTER_AUTH_TOKEN is missing or empty."}
        try:
            resp = self.complete("Reply ONLY with 'OK' for connectivity check.", timeout=15)
            lat = round(time.time() - t0, 3)
            return {
                "success": True,
                "provider": "puter",
                "model": self.model,
                "latency_s": lat,
                "response": resp.strip()
            }
        except Exception as e:
            return {
                "success": False,
                "provider": "puter",
                "error": str(e)
            }


class PuterAgnoModel(Model):
    """Agno Model adapter to use Puter.js in Agno Agents seamlessly."""

    def __init__(self, id: Optional[str] = None, token: Optional[str] = None, **kwargs):
        model_id = id or os.getenv("PUTER_MODEL", "openrouter:openrouter/free")
        self.token = token or os.getenv("PUTER_AUTH_TOKEN", "")
        self.client = PuterLlmClient(token=self.token, model=model_id)
        super().__init__(id=model_id, name="PuterAgnoModel", provider="Puter", **kwargs)

    def invoke(self, messages, **kwargs) -> ModelResponse:
        """Synchronously invoke the model with message list."""
        msgs = []
        for m in messages:
            role = getattr(m, "role", "user")
            content = getattr(m, "content", "")
            msgs.append({"role": role, "content": str(content)})

        payload = {
            "interface": "puter-chat-completion",
            "driver": "ai-chat",
            "test_mode": False,
            "method": "complete",
            "args": {
                "messages": msgs,
                "model": self.id,
                "stream": False,
                "temperature": 0.1
            }
        }

        req = urllib.request.Request(
            self.client.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=45) as res:
            data = json.loads(res.read().decode("utf-8"))
            content = data.get("result", {}).get("message", {}).get("content", "")
            return ModelResponse(content=content)

    async def ainvoke(self, messages, **kwargs) -> ModelResponse:
        return self.invoke(messages, **kwargs)

    def invoke_stream(self, messages, **kwargs) -> Iterator[ModelResponse]:
        yield self.invoke(messages, **kwargs)

    async def ainvoke_stream(self, messages, **kwargs):
        yield self.invoke(messages, **kwargs)

    def _parse_provider_response(self, response, **kwargs) -> ModelResponse:
        return ModelResponse(content=str(response))

    def _parse_provider_response_delta(self, response_delta) -> ModelResponse:
        return ModelResponse(content=str(response_delta))
