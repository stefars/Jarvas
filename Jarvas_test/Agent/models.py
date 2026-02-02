from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from setup import API_KEY


MODEL = "qwen3:1.7b-q4_K_M"


gemini_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=API_KEY,
    model_kwargs={
        "tool_config": {
            "function_calling_config": {
                "mode": "NONE"
            }
        }
    },
    temperature= 0
)

worker_gemini_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=API_KEY,
    temperature= 0
)


localLLM = ChatOllama(
    model=MODEL,
    temperature=0
)

embedding_model = OllamaEmbeddings(
    model="qwen3-embedding:0.6b",
    validate_model_on_init=True
)








