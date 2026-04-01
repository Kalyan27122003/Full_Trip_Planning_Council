# agents/groq_helper.py
"""
Shared Groq LLM helper with automatic retry + delay
to handle free-tier 6000 TPM rate limits.
"""
import os
import time
import random
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

def get_llm(temperature: float = 0.3, max_tokens: int = 800) -> ChatGroq:
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=temperature,
        max_tokens=max_tokens,
    )

def invoke_with_retry(llm: ChatGroq, prompt: str, retries: int = 4) -> str:
    """
    Invoke LLM with exponential backoff on 429 rate limit errors.
    Also adds a 4-second base delay before every call to spread
    requests across the 60-second TPM window.
    """
    # Base delay between every agent call to avoid burst
    time.sleep(4)

    for attempt in range(retries):
        try:
            response = llm.invoke(prompt)
            return response.content
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit_exceeded" in err:
                # Parse wait time from error if available, else use backoff
                wait = (2 ** attempt) * 5 + random.uniform(1, 3)
                print(f"⏳ Rate limit hit — waiting {wait:.1f}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
            else:
                raise  # Re-raise non-rate-limit errors immediately

    return "⚠️ Could not generate response after multiple retries due to rate limits."