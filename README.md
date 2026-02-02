# Jarvas: Personal Forensics Agent

**Jarvas** is an autonomous multi-agent system designed to assist in solving digital forensics CTFs (Capture The Flag). By leveraging a hierarchical agent structure, Jarvas can analyze tasks, execute Linux-based commands, and perform RAG-based information retrieval.

---

##  How It Works

Jarvas operates using a **Supervisor-Worker** architecture:

### 1. The Supervisor Tier
* **Classifier:** Analyzes the user's intent. It routes the flow to either `perform_action` (the Worker) or `informational` (direct response).
* **Supervisor LLM:** Provides high-level assistance, answers forensic questions, and suggests strategic options to the user.

### 2. The Worker Tier
* **Worker Agent:** Receives specific tasks and executes implemented tools. It is equipped with guardrails to prevent hallucinations and system instability.
* **Forensics Auditor (Classifier):** A specialized agent that verifies tool outputs.
    * **Incomplete:** It provides feedback and reasoning, triggering the Worker to attempt a new strategy.
    * **Complete:** It summarizes the findings for the user.

> **Note:** The worker can only access implemented tools, which include safety guardrails.

---

##  Specifications & Requirements
* **OS:** Linux (Tested on Ubuntu). The agent utilizes native Linux commands.
* **Environment:** Python 3.10+
* **Hardware:** Local embedding support via Ollama.

---

##  Installation

1.  **Clone the Repository**

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Ollama:**
    Ensure [Ollama](https://ollama.ai/) is installed and pull the required embedding model:
    ```bash
    ollama pull qwen3-embedding:0.6b
    ```

4.  **Environment Variables:**
    Create a `.env` file in the root directory (`/Jarvas_test`) and populate it:
    ```env
    API_KEY=your_gemini_api_key
    WORKING_DIR=/path/to/your/forensics/workspace
    ```

---

## 📚 RAG System (Knowledge Base)
Jarvas can learn from your local documentation using a Retrieval-Augmented Generation (RAG) system.

* **Place Files:** Drop `.txt` files into `/Jarvas_test/Documents/Info`.
* **Update Database:** Ask Jarvas to *"update your database"* in the chat. The agent will embed the files and make them available for query.

---



