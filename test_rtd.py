from langchain_community.document_loaders import ReadTheDocsLoader

loader = ReadTheDocsLoader("rtdocs")

docs = loader.load()