
# Imports

from langchain_chroma import Chroma
from langchain_core.documents import Document
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
import hashlib
from Agent.models import embedding_model


current_file_dir = Path(__file__).resolve().parent

# Files that can be added by the user.
txt_files_storage_path = current_file_dir.parent / "Documents" / "Info"

# Emmbeddings locations.
chromaDB_storage_path = str(current_file_dir.parent / "Documents" / "ChromaDB")









class ChromaDB:

    """
    Handles database communication and is used for RAG search retrival
    """

    def __init__(self, storage_p=chromaDB_storage_path, documents_p=txt_files_storage_path, embed_model=embedding_model):
        self.storage = storage_p
        self.text_entries = documents_p

        self.vector_store = Chroma(
            collection_name="forensics",
            embedding_function=embed_model,
            persist_directory=chromaDB_storage_path
        )


    def _get_content(self):


        """Helper function to retrieve all text files and passing them to create_document_list for embedding"""


        for file in self.text_entries.glob("*.txt"):
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()                              #Stored in a variable, expecting small files.
                yield content, file.name

    def _create_document_list(self):

        """Takes all txt files from text_entries to create Document class, uses get_content"""

        docs = []
        for content, filename in self._get_content():
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": "user",
                        "name": filename
                    }
                )
            )

        return docs

    def add_documents(self):
        docs = self._create_document_list()

        #Get list of file names
        filenames_to_update = list(set(d.metadata.get("name") for d in docs if d.metadata.get("name")))

        #If we are adding a file with the same name, we remove it first (to prevent dups)
        #basically assume a file with the same name is being updated
        if filenames_to_update:
            for fname in filenames_to_update:
                self.vector_store.delete(where={"name": fname})


        #Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        split_docs = text_splitter.split_documents(docs)


        ids = [hashlib.md5(d.page_content.encode()).hexdigest() for d in split_docs]

        self.vector_store.add_documents(documents=split_docs, ids=ids)

        # info(f"Added {len(split_docs)} chunks to the database.")



    def search(self, query, k=3):
        """
        Search and retrieve the most similar results
        """

        return self.vector_store.similarity_search(query,k=k)









