import chromadb
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)
from unstructured.partition.pdf import partition_pdf
import uuid
client = chromadb.PersistentClient(path="./my_local_db")
emb_fn = OllamaEmbeddingFunction(
    url = "http://localhost:11434",
    model_name="mxbai-embed-large:335m"
)
collection = client.get_or_create_collection(name="pdf_knowledge_base", embedding_function=emb_fn)


def ingest_pdf(file_path):
    try:
        document = partition_pdf(
            filename=file_path,
            strategy="auto",
            chunking_strategy="by_title",
            #max_characters = 10000,
            #combine_text_under_n_chars = 2000,
            #new_after_n_chars = 5000
        )
        text = []
        for doc in document:
             if 'CompositeElement' in str(type(doc)):
                text.append(doc.text)

        if len(text) > 0:
            collection.add(
                documents=text,
                metadatas=[{"source": file_path}],
                ids=[str(uuid.uuid4()) for _ in range(len(text))]
            )
        
        return text
    except Exception as e:
        return f"Error processing pdf: {str(e)}"