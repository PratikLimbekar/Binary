# src/services/local_llm_service.py

from __future__ import annotations

import json
from typing import List, Dict, Optional

import requests


class LocalLLMService:
    """
    Service for communicating with a local Ollama model.

    Features:
    - Verifies that Ollama is running.
    - Lazily initializes on first use.
    - Maintains a short conversation history.
    - Sends chat messages to Ollama's /api/chat endpoint.
    """

    def __init__(
        self,
        model_name: str = "smollm2:1.7b",
        base_url: str = "http://localhost:11434",
        max_history: int = 1,  # Minimal history - only current exchange
        timeout: int = 30,     # Reduced timeout
        keep_alive: str = "30s",  # Unload model after 30s to free memory
        system_prompt: Optional[str] = None,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.chat_url = f"{self.base_url}/api/chat"

        self.max_history = max_history
        self.timeout = timeout
        self.keep_alive = keep_alive

        self.system_prompt = (
            "You are Binary, a wise old owl assistant. Speak calmly and briefly.\n\n"
            "RULES:\n"
            "1. If the user wants an ACTION (set timer, open app, log finance), output ONLY JSON.\n"
            "2. If the user is just CHATTING or asking a question, output ONLY PLAIN TEXT.\n"
            "3. Never mix JSON and plain text.\n"
            "4. Never invent new tools.\n\n"
            "JSON FORMATS:\n"
            "- Tool: {\"type\":\"tool_call\",\"action\":\"name\",\"parameters\":{}}\n"
            "- Intent: {\"type\":\"intent\",\"name\":\"name\"}"
        )

        self.intent_block = (
            "\n\nINTENTS: 1.get_system_info: stats 2.open_app: apps 3.web_search: search 4.create_note: notes "
            "5.ask_question: info 6.music_controls: music 7.get_weather: weather 8.get_news: news "
            "9.wikipedia_search: wiki 11.set_timer: timer 12.send_email: email "
            "13.make_call: call 14.control_smart_home: smart 15.tell_joke: joke 16.translate_text: trans "
            "17.check_calendar: sched 18.add_calendar_event: create 19.set_reminder: remind "
            "20.start_focus_mode: focus 21.ambient_audio: audio 22.workspace_launcher: space 23.finance_log: finance\n\n"
            "SCHEMA: Tool:{\"type\":\"tool_call\",\"action\":\"name\",\"parameters\":{}} "
            "Intent:{\"type\":\"intent\",\"name\":\"name\",\"parameters\":{}} "
            "Chat:{\"type\":\"chat\",\"response\":\"text\"}"
        )

        self.options = {
            "temperature": 0.1,
            "num_predict": 80,  # Minimal output length
            "num_thread": 2,    # Reduced for memory efficiency
            "num_ctx": 512,     # Minimal context size to reduce memory
        }

        # Lazy initialization flag
        self._initialized = False

        # Conversation history (excluding system prompt)
        # Example:
        # [
        #   {"role": "user", "content": "Hello"},
        #   {"role": "assistant", "content": "Good evening."}
        # ]
        self.history: List[Dict[str, str]] = []

        # Reuse a single HTTP session for efficiency
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Initialization / Health Checks
    # ------------------------------------------------------------------

    def is_ollama_running(self) -> bool:
        """
        Check whether the Ollama server is available.
        Uses the lightweight /api/tags endpoint.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _ensure_initialized(self) -> None:
        """
        Lazily initialize the service on first use.
        Verifies that Ollama is reachable.
        """
        if self._initialized:
            return

        if not self.is_ollama_running():
            raise RuntimeError(
                "Ollama is not running. Start Ollama and ensure "
                "http://localhost:11434 is accessible."
            )

        self._initialized = True

    # ------------------------------------------------------------------
    # History Management
    # ------------------------------------------------------------------

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to history and trim to max_history entries.
        """
        self.history.append({"role": role, "content": content})

        # Keep only the most recent messages
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

    def clear_history(self) -> None:
        """
        Remove all conversation history.
        """
        self.history.clear()

    def _build_messages(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        include_history: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Build the message list sent to Ollama.
        """
        prompt = system_prompt or (self.system_prompt + self.intent_block)

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": prompt}
        ]

        if include_history:
            messages.extend(self.history)
            
        messages.append({"role": "user", "content": user_message})

        return messages

    # ------------------------------------------------------------------
    # Core Chat Method
    # ------------------------------------------------------------------

    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        include_history: bool = True,
    ) -> str:
        """Static chat for internal reasoning/classification."""
        self._ensure_initialized()
        messages = self._build_messages(user_message, system_prompt, include_history)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": self.options,
            "keep_alive": self.keep_alive,
        }

        try:
            response = self.session.post(self.chat_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            assistant_text = data["message"]["content"].strip()

            if include_history:
                self.add_message("user", user_message)
                self.add_message("assistant", assistant_text)
            return assistant_text
        except Exception as e:
            logging.error(f"Chat error: {e}")
            return "{\"type\": \"chat\", \"response\": \"...\"}"

    def stream_chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        include_history: bool = True,
    ):
        """Yields chunks of the response. Forces plain text for conversational flow."""
        self._ensure_initialized()
        
        # Build messages normally
        messages = self._build_messages(user_message, system_prompt, include_history)
        
        # Append the instruction as a system-level reminder at the very end
        messages.append({
            "role": "system", 
            "content": "IMPORTANT: Respond ONLY with the direct answer in PLAIN TEXT. Do NOT use JSON."
        })

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": self.options,
        }

        try:
            response = self.session.post(
                self.chat_url,
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()

            full_response = ""
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if "message" in chunk and "content" in chunk["message"]:
                        content = chunk["message"]["content"]
                        full_response += content
                        yield content
            
            # Save to history once complete
            if include_history:
                self.add_message("user", user_message)
                self.add_message("assistant", full_response)

        except Exception as e:
            yield f"Error: {str(e)}"

    # ------------------------------------------------------------------
    # Convenience Methods
    # ------------------------------------------------------------------

    def warm_up(self) -> None:
        """
        Optionally load the model into memory with a tiny prompt.
        Useful during application startup if desired.
        """
        self.chat("Hello.")

    def unload_model(self) -> None:
        """
        Hint to Ollama to unload the model immediately by setting keep_alive=0.
        """
        try:
            self.session.post(
                self.chat_url,
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": "Goodbye."}],
                    "stream": False,
                    "keep_alive": 0,
                },
                timeout=10,
            )
        except requests.RequestException:
            pass