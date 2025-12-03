import streamlit as st
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START
from mistralai import Mistral
from tavily import TavilyClient
import json
import os

# -------------------- Load Secrets --------------------
MODEL = "mistral-small-latest"
client = Mistral(api_key=st.secrets["MISTRAL_API_KEY"])
tavily = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
CHAT_HISTORY_FILE = "chat_history.json"

# -------------------- Helper --------------------
def _add_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    return left + right

# -------------------- State Definition --------------------
class MessagesState(TypedDict):
    messages: Annotated[List[BaseMessage], _add_messages]

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
    role_map = {"human": "user", "ai": "assistant", "system": "system"}

    msgs = [{"role": role_map[m.type], "content": m.content} for m in state["messages"]]
    msgs.append({
        "role": "system",
        "content": (
            "You are a search-decider. Return ONLY 'SEARCH_REQUIRED' "
            "or 'NO_SEARCH'."
        )
    })

    resp = client.chat.complete(model=MODEL, messages=msgs)
    decision = resp.choices[0].message.content.strip().upper()
    if decision not in ["SEARCH_REQUIRED", "NO_SEARCH"]:
        decision = "SEARCH_REQUIRED"
    return {"messages": [SystemMessage(content=decision)]}

# -------------------- Node 2: Tavily Search --------------------
def tavily_search_node(state: MessagesState) -> MessagesState:
    question = state["messages"][-2].content
    result = tavily.search(query=question, max_results=5)
    summary = result["results"][0]["content"] if result["results"] else "No search results."
    return {"messages": [SystemMessage(content=f"SEARCH_RESULT: {summary}")]}

# -------------------- Node 3: LLM Response --------------------
def llm_call(state: MessagesState) -> MessagesState:
    role_map = {"human": "user", "ai": "assistant", "system": "system"}

    msgs = [{"role": role_map[m.type], "content": m.content} for m in state["messages"]]
    resp = client.chat.complete(model=MODEL, messages=msgs)
    msg = resp.choices[0].message

    if msg.role == "assistant":
        out = AIMessage(content=msg.content)
    else:
        out = SystemMessage(content=msg.content)

    return {"messages": [out]}

# -------------------- Build Graph --------------------
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
st.set_page_config(page_title="LangGraph AI Agent", page_icon="🤖")

st.title("🤖 LangGraph AI Agent with Tavily + Mistral")

# Load chat memory
if "chat_memory" not in st.session_state:
    st.session_state.chat_memory = load_chat(CHAT_HISTORY_FILE)

# Show chat history
for msg in st.session_state.chat_memory["messages"]:
    if msg.type == "human":
        with st.chat_message("user"):
            st.write(msg.content)
    else:
        with st.chat_message("assistant"):
            st.write(msg.content)

# Chat input
user_input = st.chat_input("Ask me anything...")

if user_input:
    # Add user message
    st.session_state.chat_memory["messages"].append(HumanMessage(content=user_input))

    # Run agent
    st.session_state.chat_memory = agent.invoke(st.session_state.chat_memory)

    # Save memory
    save_chat(CHAT_HISTORY_FILE, st.session_state.chat_memory["messages"])

    # Display last bot reply
    last_msg = st.session_state.chat_memory["messages"][-1]

    with st.chat_message("assistant"):
        st.write(last_msg.content)

