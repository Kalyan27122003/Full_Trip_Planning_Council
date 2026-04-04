# agents/groq_helper.py
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

def invoke_with_retry(llm: ChatGroq, prompt: str, retries: int = 5) -> str:
    """Invoke LLM with exponential backoff on 429 rate limit errors."""
    time.sleep(4)  # base delay between every agent call

    for attempt in range(retries):
        try:
            response = llm.invoke(prompt)
            return response.content
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit_exceeded" in err:
                wait = (2 ** attempt) * 5 + random.uniform(1, 3)
                print(f"⏳ Rate limit — waiting {wait:.1f}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
            elif "413" in err or "tokens" in err.lower():
                # Token limit — truncate prompt and retry
                print(f"⚠️ Token limit hit — truncating prompt and retrying...")
                prompt = prompt[:int(len(prompt) * 0.7)]
                time.sleep(3)
            else:
                raise

    return "⚠️ Could not generate response after multiple retries due to rate limits. Please try again."