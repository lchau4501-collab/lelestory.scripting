import os
import sys
import re
import json
import random
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger("MultiAIProvider")

class MultiAIProvider:
    """
    3-Tier Multi-AI Provider with Dynamic Key Rotation:
    - Tier 1: Gemini Direct (Google AI Studio) - Multi-key list with automatic quota failover.
    - Tier 2: AGNES AI Gateway (OpenAI Compatible) - Multi-token list with model cascading.
    - Tier 3: Cloudflare Workers AI - Multi-token list running LLaMA 3.1 / Qwen on Cloudflare Edge.
    """

    def __init__(self):
        # 1. Parse Gemini Keys
        raw_gemini = os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY") or ""
        self.gemini_keys = [k.strip() for k in re.split(r"[\n,;]+", raw_gemini) if k.strip()]

        # 2. Parse Agnes Keys & Base URL
        raw_agnes = os.environ.get("AGNES_API_KEYS") or os.environ.get("AGNES_API_KEY") or ""
        self.agnes_keys = [k.strip() for k in re.split(r"[\n,;]+", raw_agnes) if k.strip()]
        self.agnes_base_url = os.environ.get("AGNES_BASE_URL", "https://api.agnes.ai/v1")

        # 3. Parse Cloudflare Tokens & Account ID
        raw_cf = os.environ.get("CLOUDFLARE_API_TOKENS") or os.environ.get("CLOUDFLARE_API_TOKEN") or ""
        self.cf_tokens = [k.strip() for k in re.split(r"[\n,;]+", raw_cf) if k.strip()]
        self.cf_account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "3591f5b61af3263ca14af7a1765cc954")

    def call_ai(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> Optional[str]:
        """Executes 3-Tier AI call with automatic failover."""
        # Tier 1: Gemini Direct
        if self.gemini_keys:
            shuffled_gemini = self.gemini_keys.copy()
            random.shuffle(shuffled_gemini)
            for idx, key in enumerate(shuffled_gemini):
                masked = f"{key[:6]}...****" if len(key) > 8 else "****"
                try:
                    logger.info(f"⚡ [Tier 1: Gemini Direct] Calling key [{idx+1}/{len(shuffled_gemini)}]: {masked}...")
                    res = self._call_gemini(prompt, system_prompt, key, temperature)
                    if res:
                        return res
                except Exception as e:
                    logger.warning(f"⚠️ Gemini key {masked} failed: {e}. Rotating to next key...")

        # Tier 2: Agnes AI Gateway
        if self.agnes_keys:
            shuffled_agnes = self.agnes_keys.copy()
            random.shuffle(shuffled_agnes)
            for idx, key in enumerate(shuffled_agnes):
                masked = f"{key[:6]}...****" if len(key) > 8 else "****"
                try:
                    logger.info(f"⚡ [Tier 2: Agnes Gateway] Calling key [{idx+1}/{len(shuffled_agnes)}]: {masked}...")
                    res = self._call_agnes(prompt, system_prompt, key, temperature)
                    if res:
                        return res
                except Exception as e:
                    logger.warning(f"⚠️ Agnes key {masked} failed: {e}. Rotating to next key...")

        # Tier 3: Cloudflare Workers AI
        if self.cf_tokens:
            shuffled_cf = self.cf_tokens.copy()
            random.shuffle(shuffled_cf)
            for idx, token in enumerate(shuffled_cf):
                masked = f"{token[:6]}...****" if len(token) > 8 else "****"
                try:
                    logger.info(f"⚡ [Tier 3: Cloudflare Workers AI] Calling token [{idx+1}/{len(shuffled_cf)}]: {masked}...")
                    res = self._call_cloudflare(prompt, system_prompt, token)
                    if res:
                        return res
                except Exception as e:
                    logger.warning(f"⚠️ Cloudflare token {masked} failed: {e}. Rotating to next token...")

        logger.error("🚨 All 3 AI Tiers (Gemini, Agnes, Cloudflare) exhausted or unavailable.")
        return None

    def _call_gemini(self, prompt: str, system_prompt: str, key: str, temperature: float) -> Optional[str]:
        models = ["gemini-2.5-flash", "gemini-3.7-flash", "gemini-1.5-flash"]
        for m in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature}
            }
            if system_prompt:
                payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
            res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
            if res.status_code == 200:
                data = res.json()
                parts = data.get("candidates", [])[0].get("content", {}).get("parts", [])
                text = "".join([p.get("text", "") for p in parts if p.get("text")])
                if text:
                    return text
            elif res.status_code == 429:
                raise Exception("Rate limit (429)")
        return None

    def _call_agnes(self, prompt: str, system_prompt: str, key: str, temperature: float) -> Optional[str]:
        url = f"{self.agnes_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": "gemini-2.5-flash",
            "messages": messages,
            "temperature": temperature
        }
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
        raise Exception(f"Agnes HTTP {res.status_code}: {res.text}")

    def _call_cloudflare(self, prompt: str, system_prompt: str, token: str) -> Optional[str]:
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.cf_account_id}/ai/run/@cf/meta/llama-3.1-70b-instruct"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt or "You are a professional Chinese language storyteller."},
                {"role": "user", "content": prompt}
            ]
        }
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json().get("result", {}).get("response", "")
        raise Exception(f"Cloudflare Workers AI HTTP {res.status_code}: {res.text}")
