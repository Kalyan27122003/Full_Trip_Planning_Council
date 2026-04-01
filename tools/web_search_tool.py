# tools/web_search_tool.py
import os
from dotenv import load_dotenv

load_dotenv()

def web_search(query: str, max_results: int = 3) -> str:
    """Search the web using Tavily and return formatted results."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        results = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )
        if not results.get("results"):
            return "No web results found."
        output = []
        for r in results["results"]:
            output.append(f"📌 {r.get('title', '')}\n{r.get('content', '')[:300]}")
        return "\n\n".join(output)
    except ImportError:
        # Fallback: try langchain_community wrapper
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            tool = TavilySearchResults(max_results=max_results)
            results = tool.invoke(query)
            if isinstance(results, list):
                output = []
                for r in results:
                    output.append(f"📌 {r.get('url', '')}\n{r.get('content', '')[:300]}")
                return "\n\n".join(output)
            return str(results)
        except Exception as e2:
            return f"Web search unavailable: {str(e2)}"
    except Exception as e:
        return f"Web search error: {str(e)}"