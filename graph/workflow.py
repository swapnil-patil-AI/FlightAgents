from langgraph.graph import StateGraph, START, END

from graph.state import FlightBookingState
from agents.flight_search_agent import flight_search_node
from agents.booking_agent import booking_node
from agents.confirmation_agent import confirmation_node


def get_search_graph():
    """Graph that runs only Agent 1 — flight search."""
    builder = StateGraph(FlightBookingState)
    builder.add_node("flight_search", flight_search_node)
    builder.add_edge(START, "flight_search")
    builder.add_edge("flight_search", END)
    return builder.compile()


def get_booking_graph():
    """Graph that runs Agent 2 (booking) then Agent 3 (confirmation)."""
    builder = StateGraph(FlightBookingState)
    builder.add_node("booking", booking_node)
    builder.add_node("confirmation", confirmation_node)
    builder.add_edge(START, "booking")
    builder.add_edge("booking", "confirmation")
    builder.add_edge("confirmation", END)
    return builder.compile()


_search_graph = None
_booking_graph = None


def get_search_graph_cached():
    global _search_graph
    if _search_graph is None:
        _search_graph = get_search_graph()
    return _search_graph


def get_booking_graph_cached():
    global _booking_graph
    if _booking_graph is None:
        _booking_graph = get_booking_graph()
    return _booking_graph
