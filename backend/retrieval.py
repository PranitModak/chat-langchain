import os
from contextlib import contextmanager
from typing import Iterator

from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableConfig
from langchain_community.vectorstores import Chroma

from backend.configuration import BaseConfiguration
from backend.constants import CHROMA_COLLECTION_NAME


def make_text_encoder(model: str) -> Embeddings:
    """Connect to the configured text encoder. Only Google GenAI supported."""
    provider, model_name = model.split("/", maxsplit=1)
    if provider != "google_genai":
        raise ValueError(f"Only Google GenAI embeddings are supported. Got: {provider}")
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001")


@contextmanager
def make_chroma_retriever(
    configuration: BaseConfiguration, embedding_model: Embeddings
) -> Iterator[BaseRetriever]:
    store = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embedding_model,
        persist_directory="chroma_db"
        )
    search_kwargs = {**configuration.search_kwargs}
    yield store.as_retriever(search_kwargs=search_kwargs)


@contextmanager
def make_retriever(
    config: RunnableConfig,
) -> Iterator[BaseRetriever]:
    """Create a retriever for the agent, based on the current configuration."""
    configuration = BaseConfiguration.from_runnable_config(config)
    embedding_model = make_text_encoder(configuration.embedding_model)
    match configuration.retriever_provider:
        case "chroma":
            with make_chroma_retriever(configuration, embedding_model) as retriever:
                yield retriever
        case _:
            raise ValueError(
                "Unrecognized retriever_provider in configuration. "
                f"Expected one of: chroma\n"
                f"Got: {configuration.retriever_provider}"
            )
