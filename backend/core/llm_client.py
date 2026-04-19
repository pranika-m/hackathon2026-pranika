"""
Optional Gemini client.

The agent can run fully offline via deterministic policy logic. If
`GEMINI_API_KEY` is configured, planner and evaluator may also use Gemini for
supplemental reasoning.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency at runtime
    genai = None


SYSTEM_PROMPT = """You are ShopWave's autonomous support resolution agent.
Respect the tool constraints, explain every decision, and prefer escalation
whenever policy is ambiguous or confidence is low."""


class GeminiClient:
    def __init__(self) -> None:
        self.enabled = bool(genai) and bool(os.getenv("GEMINI_API_KEY"))
        self.model = None
        if self.enabled:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=SYSTEM_PROMPT,
            )

    async def generate(self, prompt: str, temperature: float = 0.2) -> str:
        if not self.enabled or self.model is None:
            return "[LLM_DISABLED]"
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=1024,
                ),
            )
            return response.text
        except Exception as exc:
            return f"[LLM_ERROR] {exc}"

    async def generate_json(self, prompt: str, temperature: float = 0.1) -> str:
        return await self.generate(
            f"{prompt}\n\nRespond with valid JSON only.",
            temperature=temperature,
        )


_client: GeminiClient | None = None


def get_llm_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
