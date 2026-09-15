"""
Multi-AI Provider for LeLe Storybook Video Engine (@lelehoctiengtrung).
Supports intelligent multi-tier key rotation and automatic failover across:
1. Tier 1: Google Gemini API (Supports new 'AQ.Ab8RN...' and classic 'AIzaSy...' keys)
2. Tier 2: Agnes AI API Gateway (https://apihub.agnes-ai.com/v1 - OpenAI compatible)
3. Tier 3: Cloudflare Workers AI (Optional - dynamically configured via env)
"""

import os
import sys
import re
import json
import random
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("MultiAIProvider")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def parse_and_clean_keys(raw_keys: str) -> List[str]:
    """Parses, trims, and cleans multiple API keys separated by commas, newlines, semicolons, or pipes."""
    if not raw_keys or not raw_keys.strip():
        return []
    # Split by common delimiters
    tokens = re.split(r"[\n,;|]+", raw_keys)
    cleaned = []
    for t in tokens:
        clean = t.strip().strip("'\"`")
        if clean and not clean.startswith("#"):
            cleaned.append(clean)
    return cleaned


class MultiAIProvider:
    def __init__(self):
        # 1. Parse Gemini Keys (Supports new format AQ.Ab8RN... and legacy AIzaSy...)
        raw_gemini = (
            os.environ.get("GEMINI_API_KEYS")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or ""
        )
        self.gemini_keys = parse_and_clean_keys(raw_gemini)

        # 2. Parse Agnes AI Keys & Base URL (https://apihub.agnes-ai.com/v1)
        raw_agnes = (
            os.environ.get("AGNES_API_KEYS")
            or os.environ.get("AGNES_API_KEY")
            or ""
        )
        self.agnes_keys = parse_and_clean_keys(raw_agnes)
        self.agnes_base_url = (os.environ.get("AGNES_BASE_URL") or "https://apihub.agnes-ai.com/v1").rstrip("/")

        # 3. Parse Cloudflare Workers AI (Strictly optional from environment, zero hardcoded defaults)
        raw_cf = (
            os.environ.get("CLOUDFLARE_API_TOKENS")
            or os.environ.get("CLOUDFLARE_API_TOKEN")
            or ""
        )
        self.cf_tokens = parse_and_clean_keys(raw_cf)
        self.cf_account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()

    def call_ai(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> Optional[str]:
        """
        Executes multi-tier AI call with automatic key rotation and failover.
        Order: Gemini Direct -> Agnes AI Gateway -> Cloudflare Workers AI -> None (Fallback)
        """
        # =========================================================================
        # TIER 1: Google Gemini API (Supports AQ.Ab8RN... and AIzaSy... keys)
        # =========================================================================
        if self.gemini_keys:
            shuffled_gemini = self.gemini_keys.copy()
            random.shuffle(shuffled_gemini)
            for idx, key in enumerate(shuffled_gemini):
                masked_key = self._mask_key(key)
                try:
                    logger.info(f"⚡ [Tier 1: Gemini Direct] Calling key [{idx+1}/{len(shuffled_gemini)}]: {masked_key}...")
                    result = self._call_gemini(prompt, system_prompt, key, temperature)
                    if result and result.strip():
                        logger.info(f"✅ [Tier 1: Gemini Direct] Success via key {masked_key} ({len(result)} chars).")
                        return result
                except Exception as exc:
                    logger.warning(f"⚠️ [Tier 1: Gemini Direct] Key {masked_key} failed: {exc}. Rotating to next key...")

        # =========================================================================
        # TIER 2: Agnes AI Gateway (https://apihub.agnes-ai.com/v1)
        # =========================================================================
        if self.agnes_keys:
            shuffled_agnes = self.agnes_keys.copy()
            random.shuffle(shuffled_agnes)
            for idx, key in enumerate(shuffled_agnes):
                masked_key = self._mask_key(key)
                try:
                    logger.info(f"⚡ [Tier 2: Agnes Gateway] Calling key [{idx+1}/{len(shuffled_agnes)}]: {masked_key} (Endpoint: {self.agnes_base_url})...")
                    result = self._call_agnes(prompt, system_prompt, key, temperature)
                    if result and result.strip():
                        logger.info(f"✅ [Tier 2: Agnes Gateway] Success via key {masked_key} ({len(result)} chars).")
                        return result
                except Exception as exc:
                    logger.warning(f"⚠️ [Tier 2: Agnes Gateway] Key {masked_key} failed: {exc}. Rotating to next key...")

        # =========================================================================
        # TIER 3: Cloudflare Workers AI (Optional if configured)
        # =========================================================================
        if self.cf_tokens and self.cf_account_id:
            shuffled_cf = self.cf_tokens.copy()
            random.shuffle(shuffled_cf)
            for idx, token in enumerate(shuffled_cf):
                masked_token = self._mask_key(token)
                try:
                    logger.info(f"⚡ [Tier 3: Cloudflare Workers AI] Calling token [{idx+1}/{len(shuffled_cf)}]: {masked_token}...")
                    result = self._call_cloudflare(prompt, system_prompt, token)
                    if result and result.strip():
                        logger.info(f"✅ [Tier 3: Cloudflare Workers AI] Success via token {masked_token}.")
                        return result
                except Exception as exc:
                    logger.warning(f"⚠️ [Tier 3: Cloudflare Workers AI] Token {masked_token} failed: {exc}. Rotating to next token...")

        logger.error("🚨 All configured AI Tiers (Gemini, Agnes, Cloudflare) exhausted or unavailable.")
        return None

    def call_ai_json(self, prompt: str, system_prompt: str = "", temperature: float = 0.5) -> Optional[Dict[str, Any]]:
        """Calls AI and parses the response strictly as a JSON dictionary."""
        sys_p = (system_prompt + "\nReturn strictly valid JSON only with NO Markdown backticks.").strip()
        raw = self.call_ai(prompt, sys_p, temperature=temperature)
        if not raw:
            return None
        return self._extract_json(raw)

    def _call_gemini(self, prompt: str, system_prompt: str, key: str, temperature: float) -> Optional[str]:
        """
        Calls Google Gemini API.
        Compatible with both AQ.Ab8RN... and AIzaSy... keys via header + query parameter.
        """
        # Supported Gemini model hierarchy
        models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-2.5-pro",
            "gemini-1.5-pro"
        ]

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": key
        }

        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        last_error = ""
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=30)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts if p.get("text"))
                        if text:
                            return text
                elif res.status_code in [400, 401, 403]:
                    raise ValueError(f"Auth error (HTTP {res.status_code}): {res.text[:120]}")
                elif res.status_code == 429:
                    raise RuntimeError("Rate limit / Quota exceeded (HTTP 429)")
                else:
                    last_error = f"Model {model} -> HTTP {res.status_code}: {res.text[:120]}"
            except (ValueError, RuntimeError):
                raise
            except Exception as e:
                last_error = f"Model {model} -> {str(e)}"
                continue

        raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")

    def _call_agnes(self, prompt: str, system_prompt: str, key: str, temperature: float) -> Optional[str]:
        """
        Calls Agnes AI API Gateway (https://apihub.agnes-ai.com/v1/chat/completions).
        OpenAI-compatible protocol with dynamic multi-model fallback.
        """
        url = f"{self.agnes_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Agnes AI supported models
        candidate_models = [
            "gemini-2.5-flash",
            "gpt-4o-mini",
            "deepseek-chat",
            "claude-3-5-sonnet-20241022",
            "gpt-4o"
        ]

        last_error = ""
        for model in candidate_models:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=35)
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        if content:
                            return content
                elif res.status_code in [401, 403]:
                    raise ValueError(f"Agnes Auth error (HTTP {res.status_code}): {res.text[:120]}")
                elif res.status_code == 429:
                    raise RuntimeError("Agnes Rate limit (HTTP 429)")
                else:
                    last_error = f"Model {model} -> HTTP {res.status_code}: {res.text[:120]}"
            except (ValueError, RuntimeError):
                raise
            except Exception as e:
                last_error = f"Model {model} -> {str(e)}"
                continue

        raise RuntimeError(f"All Agnes AI models failed at {url}. Last error: {last_error}")

    def _call_cloudflare(self, prompt: str, system_prompt: str, token: str) -> Optional[str]:
        """Calls Cloudflare Workers AI Meta LLaMA 3.1 70B."""
        if not self.cf_account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID is not configured.")

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.cf_account_id}/ai/run/@cf/meta/llama-3.1-70b-instruct"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt or "You are a professional Chinese language educator."},
                {"role": "user", "content": prompt}
            ]
        }
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json().get("result", {}).get("response", "")
        raise RuntimeError(f"Cloudflare Workers AI HTTP {res.status_code}: {res.text[:150]}")

    @staticmethod
    def _mask_key(key: str) -> str:
        """Masks sensitive API key for safe logging (e.g., AQ.Ab8R...****)."""
        if not key:
            return "EMPTY"
        if len(key) <= 8:
            return "****"
        return f"{key[:8]}...****"

    @staticmethod
    def _extract_json(raw_text: str) -> Optional[Dict[str, Any]]:
        """Extracts and parses JSON from raw LLM markdown text output."""
        if not raw_text:
            return None
        text = raw_text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"(\{.*\})", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
        return None
