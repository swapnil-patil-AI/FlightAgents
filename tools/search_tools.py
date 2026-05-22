import os
from tavily import TavilyClient
from langchain_core.tools import tool


def get_tavily_client() -> TavilyClient:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY environment variable not set")
    return TavilyClient(api_key=api_key)


@tool
def search_flights(query: str) -> str:
    """Search for flight information on the internet using a natural language query.

    Args:
        query: Natural language search query, e.g.
               'cheapest flights from New York to London on June 15 2025'

    Returns:
        String with flight search results from the web.
    """
    client = get_tavily_client()
    results = client.search(
        query=query,
        search_depth="advanced",
        max_results=8,
        include_answer=True,
    )

    output_parts = []

    if results.get("answer"):
        output_parts.append(f"Summary:\n{results['answer']}\n")

    output_parts.append("Search Results:")
    for i, result in enumerate(results.get("results", []), 1):
        output_parts.append(
            f"\n[{i}] {result.get('title', 'No title')}\n"
            f"    URL: {result.get('url', '')}\n"
            f"    {result.get('content', '')[:500]}"
        )

    return "\n".join(output_parts)


@tool
def search_flight_prices(origin: str, destination: str, date: str, passengers: int = 1) -> str:
    """Search for specific flight prices between two cities.

    Args:
        origin: Departure city or airport code (e.g., 'New York' or 'JFK')
        destination: Arrival city or airport code (e.g., 'London' or 'LHR')
        date: Travel date in YYYY-MM-DD format
        passengers: Number of passengers (default 1)

    Returns:
        String with flight price information from multiple sources.
    """
    client = get_tavily_client()

    queries = [
        f"cheapest flights {origin} to {destination} {date} {passengers} passenger price",
        f"best flight deals {origin} {destination} {date} airline tickets",
    ]

    all_results = []
    for query in queries:
        results = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_answer=True,
        )
        if results.get("answer"):
            all_results.append(f"Finding: {results['answer']}")
        for r in results.get("results", [])[:3]:
            all_results.append(
                f"Source: {r.get('title', '')}\n"
                f"Info: {r.get('content', '')[:400]}"
            )

    return (
        f"Flight search results for {origin} → {destination} on {date} "
        f"({passengers} passenger(s)):\n\n"
        + "\n\n---\n\n".join(all_results)
    )
