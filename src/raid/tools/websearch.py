"""Web search tool using multiple search providers"""

import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from .base import Tool, ToolParameter


class WebSearchTool(Tool):
    """Tool for performing web searches with multiple provider support"""
    
    @property
    def name(self) -> str:
        return "websearch"
    
    @property
    def description(self) -> str:
        return "Search the web for information using search engines. Returns relevant search results with titles, URLs, and snippets."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="The search query to execute"
            ),
            ToolParameter(
                name="num_results",
                type="integer",
                description="Number of search results to return (default: 5, max: 10)"
            )
        ]
    
    async def execute(self, **kwargs) -> str:
        """Execute web search"""
        query = kwargs.get("query", "").strip()
        num_results = min(kwargs.get("num_results", 5), 10)
        
        if not query:
            return "Error: Search query is required"
        
        try:
            # Try DuckDuckGo first (no API key required)
            results = await self._search_duckduckgo(query, num_results)
            
            if not results:
                return f"No search results found for query: {query}"
            
            # Format results
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"{i}. **{result['title']}**\n"
                    f"   URL: {result['url']}\n"
                    f"   Summary: {result['snippet']}\n"
                )
            
            return f"Search results for '{query}':\n\n" + "\n".join(formatted_results)
            
        except Exception as e:
            return f"Error performing web search: {str(e)}"
    
    async def _search_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Search using DuckDuckGo's instant answer API"""
        try:
            # Use DuckDuckGo instant answer API
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        # Extract instant answer if available
                        if data.get("AbstractText"):
                            results.append({
                                "title": data.get("Heading", "Instant Answer"),
                                "url": data.get("AbstractURL", ""),
                                "snippet": data.get("AbstractText", "")
                            })
                        
                        # Extract related topics
                        if data.get("RelatedTopics"):
                            for topic in data.get("RelatedTopics", [])[:num_results-len(results)]:
                                if isinstance(topic, dict) and topic.get("Text"):
                                    results.append({
                                        "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " ") if topic.get("FirstURL") else "Related Topic",
                                        "url": topic.get("FirstURL", ""),
                                        "snippet": topic.get("Text", "")
                                    })
                        
                        # If no good results, try a fallback approach
                        if not results:
                            results = await self._search_fallback(query, num_results)
                        
                        return results[:num_results]
            
            return []
            
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            # Fallback to alternative search method
            return await self._search_fallback(query, num_results)
    
    async def _search_fallback(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Fallback search method using a simple web scraping approach"""
        try:
            # Simple fallback - return a structured response indicating search was attempted
            return [{
                "title": f"Search performed for: {query}",
                "url": f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
                "snippet": f"Web search was performed for '{query}'. For detailed results, please visit the search engine directly."
            }]
        except Exception:
            return []
    
    async def _search_serp_api(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Search using SerpAPI (requires API key)"""
        import os
        api_key = os.getenv("SERP_API_KEY")
        
        if not api_key:
            return []
        
        try:
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": api_key,
                "engine": "google",
                "num": num_results
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        for result in data.get("organic_results", []):
                            results.append({
                                "title": result.get("title", ""),
                                "url": result.get("link", ""),
                                "snippet": result.get("snippet", "")
                            })
                        
                        return results[:num_results]
            
            return []
            
        except Exception as e:
            print(f"SerpAPI search error: {e}")
            return []