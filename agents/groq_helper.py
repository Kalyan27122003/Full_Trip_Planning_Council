# agents/groq_helper.py
# ─────────────────────────────────────────────────────────────────────────────
# GROQ HELPER — LLM (Language Model) Setup + Rate Limit Handler
#
# All 9 agents in this project use Groq's free API to run the LLaMA 3.1 model.
# This helper provides two things:
#   1. get_llm()          → creates a ChatGroq LLM instance with given settings
#   2. invoke_with_retry() → calls the LLM with automatic retry on rate limits
#
# Why Groq instead of OpenAI?
#   - Groq is much faster (uses custom LPU hardware) and has a free tier.
#   - llama-3.1-8b-instant is a lightweight but capable open-source model.
#
# What is a rate limit (429 error)?
#   - Groq's free tier limits how many tokens/requests you can make per minute.
#   - If you hit the limit, you get a 429 error. We handle this with retry + backoff.
# ─────────────────────────────────────────────────────────────────────────────
import os
import time
import random
from langchain_groq import ChatGroq   # LangChain wrapper for Groq API
from dotenv import load_dotenv

load_dotenv()  # Load GROQ_API_KEY from .env file


def get_llm(temperature: float = 0.3, max_tokens: int = 800) -> ChatGroq:
    """
    Create and return a ChatGroq LLM instance.

    Parameters:
        temperature : Controls creativity of the output.
                      0.0 = very factual/deterministic (used for budget/safety agents)
                      0.3 = balanced (default)
                      Higher = more creative but less accurate
        max_tokens  : Maximum length of the LLM's response in tokens.
                      ~1 token ≈ 4 characters. 800 tokens ≈ 600 words.

    The API key is loaded from the GROQ_API_KEY environment variable.
    """
    return ChatGroq(
        model="llama-3.1-8b-instant",  # Fast, lightweight LLaMA 3.1 model from Meta
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=temperature,
        max_tokens=max_tokens,
    )


def invoke_with_retry(llm: ChatGroq, prompt: str, retries: int = 5) -> str:
    """
    Call the LLM with a prompt and return the text response.
    Includes automatic retry logic for two common errors:

    1. Rate limit (429 error):
       - Groq free tier limits requests per minute.
       - We wait using exponential backoff: 8s, 16s, 32s... (+ random jitter)
       - Jitter (random extra wait) prevents all agents from retrying at the same time.

    2. Token limit (413 error):
       - The prompt is too long for the model's context window.
       - We shrink the prompt to 65% of its size and retry.

    Parameters:
        llm     : ChatGroq instance (from get_llm())
        prompt  : The full instruction text to send to the LLM
        retries : Max number of retry attempts before giving up (default: 5)

    Returns:
        The LLM's text response, or an error message if all retries fail.
    """
    # Base delay between every call to avoid hitting rate limits from the start
    time.sleep(6)

    for attempt in range(retries):
        try:
            response = llm.invoke(prompt)   # Send prompt to Groq API
            return response.content         # Extract and return the text string
        except Exception as e:
            err = str(e)

            if "429" in err or "rate_limit_exceeded" in err:
                # Rate limit hit — wait longer each retry (exponential backoff)
                # attempt 0 → wait ~8s, attempt 1 → ~16s, attempt 2 → ~32s, etc.
                wait = (2 ** attempt) * 8 + random.uniform(2, 5)
                print(f"⏳ Rate limit — waiting {wait:.1f}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)

            elif "413" in err or "tokens" in err.lower():
                # Prompt too long — truncate it to 65% and try again
                print(f"⚠️ Token limit hit — truncating prompt and retrying...")
                prompt = prompt[:int(len(prompt) * 0.65)]
                time.sleep(4)

            else:
                # Unknown error — don't retry, just raise it immediately
                raise

    # All retries exhausted — return a safe fallback message
    return "⚠️ Could not generate response after multiple retries due to rate limits. Please try again."