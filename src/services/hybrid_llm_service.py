# src/services/hybrid_llm_service.py

import os
import json
import requests
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from src.services.local_llm_service import LocalLLMService

load_dotenv()

class HybridLLMService:
    """
    A robust LLM service with a 3-tier fallback system:
    1. Groq (Cloud - Llama 3.1 70B)
    2. Pollinations.ai (Cloud - Llama 3 / OpenAI compatible)
    3. Local Ollama (Local - smollm2)
    """

    def __init__(self, system_prompt: Optional[str] = None):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.pollinations_url = "https://text.pollinations.ai/openai/v1/chat/completions"
        
        # Reuse existing local service
        self.local_service = LocalLLMService(
            model_name="smollm2:1.7b",
            max_history=1
        )

        self.history: List[Dict[str, str]] = []
        self.max_history = 5

        self.system_prompt = system_prompt or (
            "You are Binary, a wise old owl assistant. Speak calmly and briefly.\n\n"
            "RULES:\n"
            "1. If the user wants an ACTION (set timer, open app, log finance), output ONLY JSON.\n"
            "2. If the user is just CHATTING or asking a question, output ONLY PLAIN TEXT.\n"
            "3. Never mix JSON and plain text.\n"
            "4. Never invent new tools.\n\n"
            "JSON FORMATS:\n"
            "- Tool: {\"type\":\"tool_call\",\"action\":\"name\",\"parameters\":{}}\n"
            "- Intent: {\"type\":\"intent\",\"name\":\"name\",\"parameters\":{}}\n"
            "- Chat: {\"type\":\"chat\",\"response\":\"text\"}\n\n"
            "TOOL SCHEMAS:\n"
            "- set_timer: {\"minutes\": number}\n"
            "- log_finance: {\"amount\": number, \"category\": string, \"description\": string}\n"
            "- play_audio: {\"track_name\": string}\n\n"
            "INTENTS:\n"
            "1.get_system_info: stats 2.open_app: apps 3.web_search: search 4.create_note: notes "
            "5.ask_question: info 6.music_controls: music 7.get_weather: weather 8.get_news: news "
            "9.wikipedia_search: wiki 11.set_timer: timer 12.send_email: email "
            "13.make_call: call 14.control_smart_home: smart 15.tell_joke: joke 16.translate_text: trans "
            "17.check_calendar: sched 18.add_calendar_event: create 19.set_reminder: remind "
            "20.start_focus_mode: focus 21.ambient_audio: audio 22.workspace_launcher: space 23.finance_log: finance\n\n"
            "SCHEMA: Tool:{\"type\":\"tool_call\",\"action\":\"name\",\"parameters\":{}} "
            "Intent:{\"type\":\"intent\",\"name\":\"name\",\"parameters\":{}} "
            "Chat:{\"type\":\"chat\",\"response\":\"text\"}"
        )

    def _get_messages(self, user_message: str, include_history: bool) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]
        if include_history:
            messages.extend(self.history)
        messages.append({"role": "user", "content": user_message})
        return messages

    def chat(self, user_message: str, include_history: bool = True) -> str:
        """Main chat entry point with fallback logic."""
        print(f"\n[AI BRAIN] Input: {user_message}")
        print("[AI BRAIN] State: Processing...")
        
        # 1. Try Groq (Tier 1)
        if self.groq_key:
            try:
                print("[AI BRAIN] Tier 1: Trying Groq (Llama 3.1 70B)...")
                response = self._chat_groq(user_message, include_history)
                if response:
                    print(f"[AI BRAIN] SUCCESS: Groq provided response.")
                    print(f"[AI BRAIN] Output: {response}\n")
                    return response
            except Exception as e:
                print(f"[AI BRAIN] Groq Failed: {e}")

        # 2. Try Pollinations (Tier 2)
        try:
            print("[AI BRAIN] Tier 2: Trying Pollinations (Llama 3)...")
            response = self._chat_pollinations(user_message, include_history)
            if response:
                print(f"[AI BRAIN] SUCCESS: Pollinations provided response.")
                print(f"[AI BRAIN] Output: {response}\n")
                return response
        except Exception as e:
            print(f"[AI BRAIN] Pollinations Failed: {e}")

        # 3. Try Local Ollama (Tier 3)
        try:
            print("[AI BRAIN] Tier 3: Falling back to Local Ollama...")
            response = self.local_service.chat(user_message, include_history=include_history)
            print(f"[AI BRAIN] SUCCESS: Local LLM provided response.")
            print(f"[AI BRAIN] Output: {response}\n")
            return response
        except Exception as e:
            print(f"[AI BRAIN] ERROR: All tiers failed: {e}")
            return json.dumps({"type": "chat", "response": "The forest is silent, and I cannot find my voice."})

    def _chat_groq(self, user_message: str, include_history: bool) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": self._get_messages(user_message, include_history),
            "temperature": 0.2,
            "max_tokens": 512
        }
        print("[AI BRAIN] Sending request to Groq API...")
        response = requests.post(self.groq_url, headers=headers, json=payload, timeout=8)
        print(f"[AI BRAIN] Received response (Status: {response.status_code})")
        if response.status_code != 200:
            print(f"[AI BRAIN] Groq Error Details: {response.text}")
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        
        if include_history:
            self._update_history(user_message, content)
        return content

    def _chat_pollinations(self, user_message: str, include_history: bool) -> Optional[str]:
        payload = {
            "model": "openai", # Map to Llama 3 on pollinations
            "messages": self._get_messages(user_message, include_history),
            "temperature": 0.2
        }
        print("[AI BRAIN] Sending request to Pollinations API...")
        response = requests.post(self.pollinations_url, json=payload, timeout=10)
        print(f"[AI BRAIN] Received response (Status: {response.status_code})")
        response.raise_for_status()
        
        # Debug: Print body to check structure
        print(f"[AI BRAIN] Pollinations Raw Body: {response.text}")
        
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
        except Exception:
            # If JSON parsing fails or keys are missing, assume it returned plain text
            print("[AI BRAIN] Pollinations: Could not parse as OpenAI JSON, using raw text.")
            content = response.text.strip()
        
        if include_history:
            self._update_history(user_message, content)
        return content

    def _update_history(self, user_message: str, assistant_message: str):
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": assistant_message})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]

    def clear_history(self):
        self.history = []
        self.local_service.clear_history()

# Global singleton
hybrid_llm = HybridLLMService()
