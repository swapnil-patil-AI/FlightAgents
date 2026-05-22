from langgraph.graph import StateGraph, START, END

from graph.state import FlightBookingState
from agents.flight_search_agent import flight_search_node
from agents.booking_agent import booking_node
from agents.confirmation_agent import confirmation_node


def build_flight_booking_graph() -> StateGraph:
    """Build and compile the 3-agent flight booking LangGraph workflow."""
    builder = StateGraph(FlightBookingState)

    builder.add_node("flight_search", flight_search_node)
    builder.add_node("booking", booking_node)
    builder.add_node("confirmation", confirmation_node)

    builder.add_edge(START, "flight_search")
    builder.add_edge("flight_search", "booking")
    builder.add_edge("booking", "confirmation")
    builder.add_edge("confirmation", END)

    return builder.compile()


# Singleton — compiled once per process
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_flight_booking_graph()
    return _graph
