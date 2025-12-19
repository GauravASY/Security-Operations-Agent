import chromadb
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)
from unstructured.partition.text import partition_text
import uuid
client = chromadb.PersistentClient(path="./my_local_db")
emb_fn = OllamaEmbeddingFunction(
    url = "http://localhost:11434",
    model_name="mxbai-embed-large:335m"
)
collection = client.get_or_create_collection(name="pdf_knowledge_base", embedding_function=emb_fn)


def ingest_txt(file_path, s3_url):
    try:
        document = partition_text(filename=file_path)
        text = [doc.text for doc in document]

        if len(text) > 0:
            collection.add(
                documents=text,
                metadatas=[{"source": file_path, "s3_url": s3_url}],
                ids=[str(uuid.uuid4()) for _ in range(len(text))]
            )
        
        return text
    except Exception as e:
        return f"Error processing pdf: {str(e)}"