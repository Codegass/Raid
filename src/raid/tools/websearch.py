"""Web search tool using multiple search providers"""

import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from .base import Tool, ToolParameter
from bs4 import BeautifulSoup
import urllib.parse


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
        """Search using DuckDuckGo HTML endpoint and parse the results."""
        # DuckDuckGo's HTML endpoint is more reliable for general search results
        # than their JSON API, which is primarily for Instant Answers.
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        print(f"DuckDuckGo search failed with status: {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    result_nodes = soup.find_all('div', class_='result')

                    for node in result_nodes[:num_results]:
                        title_node = node.find('a', class_='result__a')
                        snippet_node = node.find('a', class_='result__snippet')
                        url_node = node.find('a', class_='result__url')

                        if title_node and snippet_node and url_node:
                            # The URL is in the href attribute, but needs to be cleaned up.
                            raw_url = url_node['href']
                            # It's URL-encoded and has a DDG redirect. We can decode and extract the real URL.
                            parsed_url = urllib.parse.unquote(raw_url)
                            real_url = parsed_url.split('uddg=')[-1].split('&')[0] if 'uddg=' in parsed_url else parsed_url

                            results.append({
                                'title': title_node.get_text(strip=True),
                                'url': real_url,
                                'snippet': snippet_node.get_text(strip=True),
                            })
                    
                    return results

        except Exception as e:
            print(f"An error occurred during DuckDuckGo HTML search: {e}")
            return []
    
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