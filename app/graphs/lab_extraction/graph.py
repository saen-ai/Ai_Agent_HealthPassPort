"""LangGraph workflow definition for lab extraction."""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.graphs.lab_extraction.state import LabExtractionState
from app.graphs.lab_extraction.nodes import (
    receive_upload,
    check_encryption,
    request_password,
    decrypt_pdf,
    extract_text,
    vision_extraction,
    collect_data,
    standardize_agent,
    save_results,
    route_after_encryption_check,
    route_after_decrypt,
    route_after_extract,
)


def build_lab_extraction_graph() -> StateGraph:
    """Build the lab extraction workflow graph."""
    
    # Create the graph
    graph = StateGraph(LabExtractionState)
    
    # Add all nodes
    graph.add_node("receive_upload", receive_upload)
    graph.add_node("check_encryption", check_encryption)
    graph.add_node("request_password", request_password)
    graph.add_node("decrypt_pdf", decrypt_pdf)
    graph.add_node("extract_text", extract_text)
    graph.add_node("vision_extraction", vision_extraction)
    graph.add_node("collect_data", collect_data)
    graph.add_node("standardize_agent", standardize_agent)
    graph.add_node("save_results", save_results)
    
    # Define edges
    # Start -> Receive Upload -> Check Encryption
    graph.add_edge(START, "receive_upload")
    graph.add_edge("receive_upload", "check_encryption")
    
    # Check Encryption -> (Request Password | Extract Text)
    graph.add_conditional_edges(
        "check_encryption",
        route_after_encryption_check,
        {
            "request_password": "request_password",
            "extract_text": "extract_text",
        }
    )
    
    # Request Password -> Decrypt PDF
    graph.add_edge("request_password", "decrypt_pdf")
    
    # Decrypt PDF -> (Request Password again | Extract Text)
    graph.add_conditional_edges(
        "decrypt_pdf",
        route_after_decrypt,
        {
            "request_password": "request_password",
            "extract_text": "extract_text",
        }
    )
    
    # Extract Text -> (Vision Extraction | Collect Data)
    graph.add_conditional_edges(
        "extract_text",
        route_after_extract,
        {
            "vision_extraction": "vision_extraction",
            "collect_data": "collect_data",
        }
    )
    
    # Vision Extraction -> Collect Data
    graph.add_edge("vision_extraction", "collect_data")
    
    # Collect Data -> Standardize Agent -> Save Results -> End
    graph.add_edge("collect_data", "standardize_agent")
    graph.add_edge("standardize_agent", "save_results")
    graph.add_edge("save_results", END)
    
    return graph


# Create and compile the graph with checkpointing for human-in-the-loop
memory = MemorySaver()
lab_extraction_graph = build_lab_extraction_graph().compile(checkpointer=memory)

