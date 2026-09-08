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
    - Tier 1: Gemini Direct (Google AI Studio) - Supports both new 'AQ.Ab8RN...' and classic 'AIzaSy...' keys.
    - Tier 2: AGNES AI Gateway (OpenAI Compatible) - https://apihub.agnes-ai.com/v1
    - Tier 3: Cloudflare Workers AI - Meta LLaMA 3.1 / Qwen on Cloudflare Serverless Edge.
    """

    def __init__(self):
        # 1. Parse Gemini Keys (Supports new format AQ.Ab8RN... and legacy AIzaSy...)
        raw_gemini = os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY") or ""
        self.gemini_keys = [k.strip() for k in re.split(r"[\n,;]+", raw_gemini) if k.strip()]

        # 2. Parse Agnes Keys & Official Base URL (https://apihub.agnes-ai.com/v1)
        raw_agnes = os.environ.get("AGNES_API_KEYS") or os.environ.get("AGNES_API_KEY") or ""
        self.agnes_keys = [k.strip() for k in re.split(r"[\n,;]+", raw_agnes) if k.strip()]
        self.agnes_base_url = os.environ.get("AGNES_BASE_URL", "").strip() or "https://apihub.agnes-ai.com/v1"


        # 3. Parse Cloudflare Tokens & Account ID
        raw_cf = os.environ.get("CLOUDFLARE_API_TOKENS") or os.environ.get("CLOUDFLARE_API_TOKEN") or ""
        self.cf_tokens = [k.strip() for k in re.split(r"[\n,;]+", raw_cf) if k.strip()]
        self.cf_account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "3591f5b61af3263ca14af7a1765cc954")

    def call_ai(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> Optional[str]:
        """Executes 3-Tier AI call with automatic failover and key rotation."""
        # --- TIER 1: Gemini Direct ---
        if self.gemini_keys:
            shuffled_gemini = self.gemini_keys.copy()
            random.shuffle(shuffled_gemini)
            for idx, key in enumerate(shuffled_gemini):
                masked = f"{key[:8]}...****" if len(key) > 10 else "****"
                try:
                    logger.info(f"⚡ [Tier 1: Gemini Direct] Calling key [{idx+1}/{len(shuffled_gemini)}]: {masked}...")
                    res = self._call_gemini(prompt, system_prompt, key, temperature)
                    if res:
                        return res
                except Exception as e:
                    logger.warning(f"⚠️ Gemini key {masked} failed: {e}. Rotating to next key...")

        # --- TIER 2: Agnes AI Gateway ---
        if self.agnes_keys:
            shuffled_agnes = self.agnes_keys.copy()
            random.shuffle(shuffled_agnes)
            for idx, key in enumerate(shuffled_agnes):
                masked = f"{key[:8]}...****" if len(key) > 10 else "****"
                try:
                    logger.info(f"⚡ [Tier 2: Agnes Gateway] Calling key [{idx+1}/{len(shuffled_agnes)}]: {masked} (Endpoint: {self.agnes_base_url})...")
                    res = self._call_agnes(prompt, system_prompt, key, temperature)
                    if res:
                        return res
                except Exception as e:
                    logger.warning(f"⚠️ Agnes key {masked} failed: {e}. Rotating to next key...")

        # --- TIER 3: Cloudflare Workers AI ---
        if self.cf_tokens:
            shuffled_cf = self.cf_tokens.copy()
            random.shuffle(shuffled_cf)
            for idx, token in enumerate(shuffled_cf):
                masked = f"{token[:8]}...****" if len(token) > 10 else "****"
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
        # Google AI Studio API: supports ?key= or x-goog-api-key header for both AQ.Ab8RN and AIzaSy keys
        models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro"]
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": key
        }

        
        last_err = ""
        for m in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature}
            }
            if system_prompt:
                payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    parts = data.get("candidates", [])[0].get("content", {}).get("parts", [])
                    text = "".join([p.get("text", "") for p in parts if p.get("text")])
                    if text:
                        return text
                elif res.status_code == 429:
                    raise Exception("Rate limit (429)")
                else:
                    last_err = f"HTTP {res.status_code}: {res.text[:150]}"
            except Exception as e:
                last_err = str(e)
                if "429" in str(e):
                    raise
                continue
        raise Exception(f"Gemini calls failed across models. Last: {last_err}")


    def _call_agnes(self, prompt: str, system_prompt: str, key: str, temperature: float) -> Optional[str]:
        url = f"{self.agnes_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Test candidate models on Agnes
        candidate_models = ["gemini-2.5-flash", "gpt-4o-mini", "claude-3-5-sonnet", "deepseek-chat"]
        for mod in candidate_models:
            payload = {
                "model": mod,
                "messages": messages,
                "temperature": temperature
            }
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=30)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
            except Exception as e:
                err_msg = str(e)
                try:
                    if hasattr(e, 'response') and e.response is not None:
                        err_msg = f"HTTP {e.response.status_code}: {e.response.text[:150]}"
                except Exception:
                    pass
                last_err = f"Model {mod} -> {err_msg}"
                continue
        raise Exception(f"Agnes HTTP calls failed across models at {url}. Last: {last_err}")

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

