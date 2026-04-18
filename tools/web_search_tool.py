# tools/web_search_tool.py
# This module performs web searches using Tavily AI Search API.
# It tries the official Tavily client first, and falls back to the
# LangChain community wrapper if the primary library isn't installed.

import os
from dotenv import load_dotenv

# Load environment variables from .env file (e.g., TAVILY_API_KEY)
load_dotenv()


def web_search(query: str, max_results: int = 3) -> str:
    """
    Searches the web using Tavily and returns formatted results.

    Args:
        query:       The search query string (e.g., "best hotels in Goa").
        max_results: Maximum number of results to return (default: 3).

    Returns:
        A formatted string with result titles and content snippets,
        or an error/unavailability message if the search fails.

    Strategy:
        1. Try the official `tavily-python` client (preferred).
        2. If not installed, fall back to `langchain_community` Tavily wrapper.
        3. If both fail, return an error message.
    """
    try:
        # ── PRIMARY: Official Tavily Python Client ───────────────────────
        from tavily import TavilyClient

        # Initialize the Tavily client using the API key from .env
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

        # Perform the search
        # "search_depth=basic" is faster and cheaper; use "advanced" for deeper results
        results = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )

        # If Tavily returned no results, inform the caller
        if not results.get("results"):
            return "No web results found."

        # Format each result as "📌 Title\nContent snippet (first 300 chars)"
        output = []
        for r in results["results"]:
            output.append(f"📌 {r.get('title', '')}\n{r.get('content', '')[:300]}")

        # Join all results with a blank line between them for readability
        return "\n\n".join(output)

    except ImportError:
        # ── FALLBACK: LangChain Community Tavily Wrapper ─────────────────
        # Reached here if `tavily-python` package is not installed.
        # The LangChain wrapper provides similar functionality as an alternative.
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults

            # Initialize the LangChain Tavily tool with the same result limit
            tool = TavilySearchResults(max_results=max_results)

            # Run the search — LangChain returns a list of dicts with 'url' and 'content'
            results = tool.invoke(query)

            if isinstance(results, list):
                # Format each result as "📌 URL\nContent snippet (first 300 chars)"
                # Note: LangChain wrapper returns 'url' instead of 'title'
                output = []
                for r in results:
                    output.append(f"📌 {r.get('url', '')}\n{r.get('content', '')[:300]}")
                return "\n\n".join(output)

            # If results aren't a list (unexpected format), return as plain string
            return str(results)

        except Exception as e2:
            # Both the primary client and the fallback failed
            return f"Web search unavailable: {str(e2)}"

    except Exception as e:
        # Catch any other errors from the primary Tavily client
        # (e.g., invalid API key, network timeout, rate limit exceeded)
        return f"Web search error: {str(e)}"