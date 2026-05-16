import os
from langchain_community.document_loaders import UnstructuredXMLLoader
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA

def setup_rag_system(xml_path):
    # XML books loader
    loader = UnstructuredXMLLoader(xml_path)
    documents = loader.load()

    # chunking
    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)

    # create Embeddings and save in ChromaDB (Vector Store)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_db = Chroma.from_documents(documents=texts, embedding=embeddings, persist_directory="./chroma_db")

    # config LLM
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

    # cadena de retrieval
    rag_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_db.as_retriever()
    )
    return rag_chain