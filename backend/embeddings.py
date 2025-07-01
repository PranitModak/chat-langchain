from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings


def get_embeddings_model() -> Embeddings:
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001")
