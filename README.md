# 🤖 BoudyPilot 1.3

BoudyPilot 1.3 is an AI-powered assistant built with **Streamlit**, **LangGraph**, **Mistral LLM**, and **Tavily API**. It provides precise, context-aware responses while leveraging external search when necessary. Each user has a dedicated chat memory for personalized interactions.

🌐 **Live Demo:** [BoudyPilot 1.1 Demo](https://boudypilot-v1.streamlit.app/)

---

## 🚀 Features

- Contextual AI responses using Mistral LLM.
- Dynamic decision-making to determine if online search is required.
- Search integration with Tavily API for verified information.
- Persistent chat memory per user.
- Streamlit-based interactive chat interface.
- Minimal hallucinations through guided LLM prompts.

---

## 🧩 Tech Stack

- **Frontend / UI:** [Streamlit](https://streamlit.io/)  
- **AI / LLM:** [Mistral Large 2512](https://mistral.ai/) via `mistralai` Python SDK  
- **Graph-based Agent:** [LangGraph](https://github.com/langgraph/langgraph) for workflow orchestration  
- **Search / Knowledge API:** [Tavily](https://www.tavily.com/)  
- **Storage:** JSON files for per-user chat memory  
- **Python Libraries:** `uuid`, `typing`, `json`, `os`  

---

## 📝 Agent Workflow

The BoudyPilot workflow consists of three main nodes orchestrated using LangGraph:

### 1️⃣ User Identification & Chat Memory
- A unique `user_id` is generated per user session using `uuid`.
- Chat history is loaded from a JSON file named `chat_history_{user_id}.json`.
- Memory is updated and persisted after every interaction.

---

### 2️⃣ Node 1: Search Decider
- Function: `decide_search_llm`
- The agent inspects the latest user message.
- Calls the **Mistral LLM** to decide whether the question requires an online search.
- Response: `"SEARCH_REQUIRED"` or `"NO_SEARCH"`.
- Decision drives the next step in the workflow.

---

### 3️⃣ Node 2: Tavily Search
- Function: `tavily_search_node`
- Triggered only if the decision is `"SEARCH_REQUIRED"`.
- Performs a search via **Tavily API** with up to 3 results.
- Returns a summarized, clean version of search results.
- Prepends `"SEARCH_RESULT:"` to the message for the next node.

---

### 4️⃣ Node 3: Final LLM Response
- Function: `llm_call`
- Aggregates user messages and search results (if available).
- Sends a structured prompt to **Mistral LLM** emphasizing:
  - No hallucinations.
  - Use only provided information.
  - Respond `"I am not sure."` if unsure.
- Returns a precise AI-generated response.

---

### 5️⃣ Streamlit Chat Interface
- Displays previous messages from the user's chat history.
- Accepts new user input via `st.chat_input`.
- Updates the memory after each interaction.
- Shows the assistant's response in the chat UI.

---

## 📁 Memory Persistence
- Chat history is saved in JSON format per user.
- Each message is stored with its type (`human`, `ai`, `system`) and content.
- Ensures continuity across sessions for personalized interactions.

---

## ⚡ How It Works Step-by-Step

1. User opens the Streamlit app or visits the [live demo](https://boudypilot-v1.streamlit.app/).
2. The app assigns a unique `user_id` and loads previous chat history.
3. User submits a query.
4. **Node 1:** Agent decides if online search is needed.
5. **Node 2 (optional):** Performs Tavily search if required.
6. **Node 3:** LLM generates the final response using context + search results.
7. Response is displayed in Streamlit.
8. Chat history is saved for future sessions.

---
![agent diagram](https://github.com/user-attachments/assets/87169d62-1c17-4b33-a1a9-1f9a705ea40e)

