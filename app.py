import streamlit as st
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START
from mistralai import Mistral
from tavily import TavilyClient
import json
import os
import uuid

# -------------------- Load Secrets --------------------
MODEL = "mistral-large-2512"  # Updated model
client = Mistral(api_key=st.secrets["MISTRAL_API_KEY"])
tavily = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])

# -------------------- Helper --------------------
def _add_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    return left + right

# -------------------- State Definition --------------------
class MessagesState(TypedDict):
    messages: Annotated[List[BaseMessage], _add_messages]

# -------------------- User Identification --------------------
if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())
user_id = st.session_state["user_id"]
CHAT_MEMORY_FILE = f"chat_history_{user_id}.json"

# -------------------- Memory Persistence --------------------
def save_chat(filename, messages):
    data = [{"type": m.type, "content": m.content} for m in messages]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_chat(filename):
    if not os.path.exists(filename):
        return {"messages": []}
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    messages = []
    for m in data:
        if m["type"] == "human":
            messages.append(HumanMessage(content=m["content"]))
        elif m["type"] == "ai":
            messages.append(AIMessage(content=m["content"]))
        else:
            messages.append(SystemMessage(content=m["content"]))
    return {"messages": messages}

# -------------------- Node 1: Search-Decider --------------------
def decide_search_llm(state: MessagesState) -> MessagesState:
    last_user = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
    msgs = [
        {"role": "system", "content": (
            "You decide if the question needs online search. "
            "Respond ONLY with SEARCH_REQUIRED or NO_SEARCH."
        )},
        {"role": "user", "content": last_user}
    ]
    resp = client.chat.complete(model=MODEL, messages=msgs, temperature=0.0)
    decision = resp.choices[0].message.content.strip().upper()
    if decision not in ["SEARCH_REQUIRED", "NO_SEARCH"]:
        decision = "SEARCH_REQUIRED"
    return {"messages": [SystemMessage(content=decision)]}

# -------------------- Node 2: Tavily Search --------------------
def tavily_search_node(state: MessagesState) -> MessagesState:
    question = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
    result = tavily.search(query=question, max_results=3)
    clean_summary = "\n".join([r["content"] for r in result["results"]])
    return {"messages": [SystemMessage(content=f"SEARCH_RESULT: {clean_summary}")]}

# -------------------- Node 3: Final LLM Response --------------------
def llm_call(state: MessagesState) -> MessagesState:
    clean_msgs = []

    for m in state["messages"]:
        if isinstance(m, HumanMessage):
            clean_msgs.append({"role": "user", "content": m.content})
        if m.content.startswith("SEARCH_RESULT:"):
            clean_msgs.append({
                "role": "system",
                "content": "Here is verified search info:\n" + m.content.replace("SEARCH_RESULT:", "").strip()
            })

    clean_msgs.insert(0, {
        "role": "system",
        "content": (
            "You are a precise AI assistant. Do NOT hallucinate. "
            "Only use provided information. "
            "If unsure, respond: 'I am not sure.'"
        )
    })

    resp = client.chat.complete(model=MODEL, messages=clean_msgs, temperature=0.0, max_tokens=1024)
    return {"messages": [AIMessage(content=resp.choices[0].message.content)]}

# -------------------- Build LangGraph --------------------
builder = StateGraph(MessagesState)
builder.add_node("decide_search", decide_search_llm)
builder.add_node("search_node", tavily_search_node)
builder.add_node("llm_call", llm_call)

builder.add_edge(START, "decide_search")
builder.add_conditional_edges(
    "decide_search",
    lambda s: s["messages"][-1].content,
    {"SEARCH_REQUIRED": "search_node", "NO_SEARCH": "llm_call"},
)
builder.add_edge("search_node", "llm_call")
agent = builder.compile()

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="BoudyPilot 1.1", page_icon="🤖")
st.title("🤖 BoudyPilot 1.1 — AI Agent")

# Load chat memory per user
if "chat_memory" not in st.session_state:
    st.session_state.chat_memory = load_chat(CHAT_MEMORY_FILE)

# Display chat history
for msg in st.session_state.chat_memory["messages"]:
    with st.chat_message("user" if msg.type == "human" else "assistant"):
        st.write(msg.content)

# Chat input
user_input = st.chat_input("Ask me anything...")

if user_input:
    # Add user message
    st.session_state.chat_memory["messages"].append(HumanMessage(content=user_input))

    # Run agent
    st.session_state.chat_memory = agent.invoke(st.session_state.chat_memory)

    # Save memory
    save_chat(CHAT_MEMORY_FILE, st.session_state.chat_memory["messages"])

    # Display last bot reply
    last_msg = st.session_state.chat_memory["messages"][-1]
    with st.chat_message("assistant"):
        st.write(last_msg.content)

