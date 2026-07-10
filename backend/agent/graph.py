"""LangGraph agent graph definition."""

import os
from typing import Dict, Any, TypedDict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.agent.prompts import SYSTEM_PROMPT


# Define state schema for LangGraph
class GraphState(TypedDict):
    """State for the LangGraph agent."""
    messages: List[Dict[str, str]]  # List of {"role": "user|assistant", "content": str}
    conversation_turn: int


# Initialize LLM
def get_llm():
    """Get LangChain LLM instance for Google Gemini."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set in environment")
    
    from google.generativeai import configure, GenerativeModel as GenAIModel
    
    configure(api_key=api_key)
    
    # Create wrapper for raw Google generative AI model
    class SimpleGeminiWrapper:
        def __init__(self):
            self.model = GenAIModel(model_name="gemini-flash-latest")
            
        def invoke(self, messages):
            # Convert LangChain messages to simple format
            text_messages = []
            for msg in messages:
                text_messages.append(f"{msg.type}: {msg.content}")
            
            prompt = "\n".join(text_messages)
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            
            # Return LangChain-compatible response
            from langchain_core.messages import AIMessage
            return AIMessage(content=response.text)
    
    return SimpleGeminiWrapper()


def process_message_node(state: GraphState) -> Dict[str, Any]:
    """
    Node that processes user message and generates AI response.
    
    This is the main node of the conversation graph.
    """
    try:
        llm = get_llm()
        
        # Get conversation messages
        messages_list = state.get("messages", [])
        
        # Build messages for LLM
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        chat_messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for msg in messages_list:
            if msg["role"] == "user":
                chat_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                chat_messages.append(AIMessage(content=msg["content"]))
        
        # Call LLM
        response = llm.invoke(chat_messages)
        response_text = response.content
        
        # Add assistant response to messages list
        new_messages = messages_list.copy() if messages_list else []
        new_messages.append({"role": "assistant", "content": response_text})
        
        turn = state.get("conversation_turn", 0) + 1
        
        return {
            "messages": new_messages,
            "conversation_turn": turn,
        }
    
    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        new_messages = state.get("messages", []).copy() if state.get("messages") else []
        new_messages.append({"role": "assistant", "content": f"Désolé, j'ai rencontré une erreur. {error_msg}"})
        
        return {
            "messages": new_messages,
            "conversation_turn": state.get("conversation_turn", 0) + 1,
        }


def create_agent_graph():
    """
    Create the LangGraph graph for the agent.
    
    Simple 1-step graph:
    - Receives user message
    - Processes with LLM
    - Returns AI response
    """
    from langgraph.graph import StateGraph, END
    
    # Create graph with GraphState
    graph_builder = StateGraph(GraphState)
    
    # Add the process_message node
    graph_builder.add_node("process_message", process_message_node)
    
    # Set entry point
    graph_builder.set_entry_point("process_message")
    
    # Add edge to END
    graph_builder.add_edge("process_message", END)
    
    # Compile the graph
    graph = graph_builder.compile()
    
    return graph


# Global graph instance
agent_graph = None


def get_agent_graph():
    """Get or create the agent graph."""
    global agent_graph
    if agent_graph is None:
        agent_graph = create_agent_graph()
    return agent_graph

