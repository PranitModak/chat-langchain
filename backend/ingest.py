"""Load html from files, clean up, split, ingest into ChromaDB."""
import logging
import os
import re
import subprocess
import tempfile
import shutil
from typing import Optional, List
from pathlib import Path

from bs4 import BeautifulSoup, SoupStrainer
from langchain_community.document_loaders import RecursiveUrlLoader, SitemapLoader, ReadTheDocsLoader
from langchain.indexes import SQLRecordManager, index
from langchain.utils.html import PREFIXES_TO_IGNORE_REGEX, SUFFIXES_TO_IGNORE_REGEX
from langchain_text_splitters import RecursiveCharacterTextSplitter
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from backend.embeddings import get_embeddings_model
from backend.parser import langchain_docs_extractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHROMA_COLLECTION_NAME = "docs"

# Repository configurations for different ingestion modes
REPO_CONFIGS = {
    "godot": {
        "url": "https://github.com/godotengine/godot-docs",
        "branch": "master",
        "docs_path": ".",
        "build_command": "python -m sphinx -T -b html -d _build/doctrees -D language=en . _build/html",
        "requirements": ["sphinx"],
        "readthedocs_config": ".readthedocs.yml"
    },
    "terrain3d": {
        "url": "https://github.com/TokisanGames/Terrain3D",
        "branch": "main", 
        "docs_path": ".",
        "build_command": "python -m sphinx -T -b html -d _build/doctrees -D language=en . _build/html",
        "requirements": ["sphinx"],
        "readthedocs_config": ".readthedocs.yaml"
    },
    "voxeltools": {
        "url": "https://github.com/Zylann/godot_voxel",
        "branch": "master",
        "docs_path": "doc",
        "build_command": "python -m mkdocs build --clean --site-dir _build/html --config-file doc/mkdocs.yml",
        "requirements": ["mkdocs"],
        "readthedocs_config": "doc/mkdocs.yml"
    }
}

def metadata_extractor(
    meta: dict, soup: BeautifulSoup, title_suffix: Optional[str] = None
) -> dict:
    title_element = soup.find("title")
    description_element = soup.find("meta", attrs={"name": "description"})
    html_element = soup.find("html")
    title = title_element.get_text() if title_element else ""
    if title_suffix is not None:
        title += title_suffix

    def safe_get(element, attr, default=""):
        from bs4 import Tag
        return element.get(attr, default) if element and isinstance(element, Tag) else default

    return {
        "source": meta["loc"],
        "title": title,
        "description": safe_get(description_element, "content"),
        "language": safe_get(html_element, "lang"),
        **meta,
    }


def load_langchain_docs():
    return SitemapLoader(
        "https://python.langchain.com/sitemap.xml",
        filter_urls=["https://python.langchain.com/"],
        parsing_function=langchain_docs_extractor,
        default_parser="lxml",
        bs_kwargs={
            "parse_only": SoupStrainer(
                name=("article", "title", "html", "lang", "content")
            ),
        },
        meta_function=metadata_extractor,
    ).load()


def load_langgraph_docs():
    return SitemapLoader(
        "https://langchain-ai.github.io/langgraph/sitemap.xml",
        parsing_function=simple_extractor,
        default_parser="lxml",
        bs_kwargs={"parse_only": SoupStrainer(name=("article", "title"))},
        meta_function=lambda meta, soup: metadata_extractor(
            meta, soup, title_suffix=" | 🦜🕸️LangGraph"
        ),
    ).load()


def load_langsmith_docs():
    return RecursiveUrlLoader(
        url="https://docs.smith.langchain.com/",
        max_depth=8,
        extractor=simple_extractor,
        prevent_outside=True,
        use_async=True,
        timeout=600,
        # Drop trailing / to avoid duplicate pages.
        link_regex=(
            f"href=[\"']{PREFIXES_TO_IGNORE_REGEX}((?:{SUFFIXES_TO_IGNORE_REGEX}.)*?)"
            r"(?:[\#'\"]|\/[\#'\"])"
        ),
        check_response_status=True,
    ).load()


def simple_extractor(html: str | BeautifulSoup) -> str:
    if isinstance(html, str):
        soup = BeautifulSoup(html, "lxml")
    elif isinstance(html, BeautifulSoup):
        soup = html
    else:
        raise ValueError(
            "Input should be either BeautifulSoup object or an HTML string"
        )
    return re.sub(r"\n\n+", "\n\n", soup.text).strip()


def load_api_docs():
    return RecursiveUrlLoader(
        url="https://api.python.langchain.com/en/latest/",
        max_depth=8,
        extractor=simple_extractor,
        prevent_outside=True,
        use_async=True,
        timeout=600,
        # Drop trailing / to avoid duplicate pages.
        link_regex=(
            f"href=[\"']{PREFIXES_TO_IGNORE_REGEX}((?:{SUFFIXES_TO_IGNORE_REGEX}.)*?)"
            r"(?:[\#'\"]|\/[\#'\"])"
        ),
        check_response_status=True,
        exclude_dirs=(
            "https://api.python.langchain.com/en/latest/_sources",
            "https://api.python.langchain.com/en/latest/_modules",
        ),
    ).load()


def load_godot_docs():
    # Godot docs have a sitemap
    return SitemapLoader(
        "https://docs.godotengine.org/en/stable/sitemap.xml",
        default_parser="lxml",
        bs_kwargs={
            "parse_only": SoupStrainer(
                name=("article", "title", "html", "lang", "content")
            ),
        },
        meta_function=metadata_extractor,
    ).load()


def load_terrain3d_docs():
    # Terrain3D docs have a sitemap
    return SitemapLoader(
        "https://terrain3d.readthedocs.io/sitemap.xml",
        default_parser="lxml",
        bs_kwargs={
            "parse_only": SoupStrainer(
                name=("article", "title", "html", "lang", "content")
            ),
        },
        meta_function=metadata_extractor,
    ).load()


def load_voxeltools_docs():
    # Voxel Tools docs have a sitemap
    return SitemapLoader(
        "https://voxel-tools.readthedocs.io/sitemap.xml",
        default_parser="lxml",
        bs_kwargs={
            "parse_only": SoupStrainer(
                name=("article", "title", "html", "lang", "content")
            ),
        },
        meta_function=metadata_extractor,
    ).load()


def clone_and_build_docs(repo_name: str, temp_dir: str) -> str:
    """Clone a repository and build its documentation locally."""
    config = REPO_CONFIGS[repo_name]
    repo_dir = os.path.join(temp_dir, repo_name)
    
    logger.info(f"Cloning {repo_name} repository...")
    subprocess.run([
        "git", "clone", "--depth", "1", 
        "-b", config["branch"], 
        config["url"], repo_dir
    ], check=True)
    
    # Change to repo directory
    os.chdir(repo_dir)
    
    # Install requirements if they exist
    requirements_file = os.path.join(config["docs_path"], "requirements.txt")
    if os.path.exists(requirements_file):
        logger.info(f"Installing requirements for {repo_name}...")
        subprocess.run([
            "python", "-m", "pip", "install", "-r", requirements_file
        ], check=True)
    
    # Install build requirements
    for req in config["requirements"]:
        subprocess.run([
            "python", "-m", "pip", "install", req
        ], check=True)
    
    # Build documentation
    logger.info(f"Building documentation for {repo_name}...")
    build_dir = os.path.join(repo_dir, config["docs_path"], "_build", "html")
    subprocess.run(config["build_command"].split(), cwd=os.path.join(repo_dir, config["docs_path"]), check=True)
    
    return build_dir

def load_docs_from_sphinx_build(repo_name: str) -> List:
    """Load documentation from a locally built Sphinx site."""
    with tempfile.TemporaryDirectory() as temp_dir:
        build_dir = clone_and_build_docs(repo_name, temp_dir)
        loader = ReadTheDocsLoader(build_dir)
        return loader.load()

def load_docs_with_gitingest(repo_name: str) -> List:
    """Load documentation using gitingest from repository."""
    try:
        from gitingest import ingest
        from langchain_core.documents import Document
    except ImportError:
        logger.error("gitingest not installed. Install with: uv pip install gitingest")
        return []
    
    config = REPO_CONFIGS[repo_name]
    logger.info(f"Extracting docs from {repo_name} using gitingest...")
    
    # Use gitingest to extract documentation
    summary, tree, content = ingest(config["url"])
    
    # Convert to LangChain documents
    docs = []
    if content:
        # Split content into manageable chunks
        doc = Document(
            page_content=content,
            metadata={
                "source": config["url"],
                "title": f"{repo_name} Documentation",
                "method": "gitingest"
            }
        )
        docs.append(doc)
    
    return docs

def ingest_docs(wipe: bool = False, mode: str = "web"):
    """
    Ingest documentation using the specified mode.
    
    Args:
        wipe: Whether to wipe existing Chroma collection
        mode: Ingestion mode - "web", "sphinx", or "gitingest"
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
    embedding = get_embeddings_model()
    
    all_docs = []
    
    if mode == "web":
        # Original web scraping approach
        logger.info("Using web scraping mode...")
        docs_godot = load_godot_docs()
        logger.info(f"Loaded {len(docs_godot)} docs from Godot documentation")
        docs_terrain3d = load_terrain3d_docs()
        logger.info(f"Loaded {len(docs_terrain3d)} docs from Terrain3D documentation")
        docs_voxeltools = load_voxeltools_docs()
        logger.info(f"Loaded {len(docs_voxeltools)} docs from Voxel Tools documentation")
        all_docs = docs_godot + docs_terrain3d + docs_voxeltools
        
    elif mode == "sphinx":
        # Local Sphinx build approach
        logger.info("Using local Sphinx build mode...")
        for repo_name in REPO_CONFIGS.keys():
            try:
                docs = load_docs_from_sphinx_build(repo_name)
                logger.info(f"Loaded {len(docs)} docs from {repo_name} (Sphinx build)")
                all_docs.extend(docs)
            except Exception as e:
                logger.error(f"Failed to build docs for {repo_name}: {e}")
                
    elif mode == "gitingest":
        # Direct repository access with gitingest
        logger.info("Using gitingest mode...")
        for repo_name in REPO_CONFIGS.keys():
            try:
                docs = load_docs_with_gitingest(repo_name)
                logger.info(f"Loaded {len(docs)} docs from {repo_name} (gitingest)")
                all_docs.extend(docs)
            except Exception as e:
                logger.error(f"Failed to extract docs for {repo_name}: {e}")
    
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'web', 'sphinx', or 'gitingest'")

    docs_transformed = text_splitter.split_documents(all_docs)
    docs_transformed = [
        doc for doc in docs_transformed if len(doc.page_content) > 10
    ]

    for doc in docs_transformed:
        if "source" not in doc.metadata:
            doc.metadata["source"] = ""
        if "title" not in doc.metadata:
            doc.metadata["title"] = ""
        if "method" not in doc.metadata:
            doc.metadata["method"] = mode

    # Save all ingested docs to a text file for inspection
    with open(f"ingested_docs_{mode}.txt", "w", encoding="utf-8") as f:
        for i, doc in enumerate(docs_transformed):
            f.write(f"--- Document {i+1} ---\n")
            f.write(f"Source: {doc.metadata.get('source', '')}\n")
            f.write(f"Title: {doc.metadata.get('title', '')}\n")
            f.write(f"Method: {doc.metadata.get('method', '')}\n")
            f.write(f"Content:\n{doc.page_content}\n\n")

    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embedding,
        persist_directory="chroma_db"
    )
    if wipe:
        # Wipe the collection if requested
        # Chroma requires a valid filter; this deletes all docs with id not empty string
        vectorstore._collection.delete(where={"id": {"$ne": ""}})
        logger.info("Wiped existing Chroma collection.")
    vectorstore.add_documents(docs_transformed)
    logger.info(f"Chroma now has this many vectors: {vectorstore._collection.count()}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest docs into Chroma.")
    parser.add_argument("--wipe", action="store_true", help="Wipe existing Chroma collection before ingesting.")
    parser.add_argument("--mode", choices=["web", "sphinx", "gitingest"], default="web", 
                       help="Ingestion mode: web (scraping), sphinx (local build), or gitingest (direct repo)")
    args = parser.parse_args()
    ingest_docs(wipe=args.wipe, mode=args.mode)
