import os
import sys

sys.modules['google._upb._message'] = None
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import xml.etree.ElementTree as ET
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from queries import (
    NAMESPACES, XPATH_USERS, XPATH_BOOKS,
    XPATH_USER_NAME, XPATH_USER_LEVEL, XPATH_USER_THEME,
    XPATH_BOOK_TITLE, XPATH_BOOK_GENRE, XPATH_BOOK_REQ_LEVEL
)

app = FastAPI(title="Semantic Web RAG Engine - Big Homework 2")

# permitir conexiones desde el servidor Java de Igna
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatQuery(BaseModel):
    question: str

DB_DIR = "./chroma_db"
RDF_PATH = "../ontology/data_books.rdf"
rag_chain = None

def load_and_vectorize_rdf():
    global rag_chain
    
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("ERROR: La variable de entorno GEMINI_API_KEY no está configurada en Windows.")

    # parsear el archivo RDF/XML
    try:
        tree = ET.parse(RDF_PATH)
        root = tree.getroot()
    except Exception as e:
        raise ValueError(f"Error al abrir el archivo RDF: {str(e)}")
    
    documents = []

    # ingestamos datos de Usuarios (Ex 7.3)
    for user_desc in root.findall(XPATH_USERS, NAMESPACES):
        name = user_desc.find(XPATH_USER_NAME, NAMESPACES).text
        
        level_node = user_desc.find(XPATH_USER_LEVEL, NAMESPACES)
        level = level_node.text if level_node is not None else "Unknown"
        
        theme_node = user_desc.find(XPATH_USER_THEME, NAMESPACES)
        theme = theme_node.text if theme_node is not None else "Unknown"
        
        user_text = f"User profile: {name}. Has a reading level of {level} and prefers the theme or genre {theme}."
        documents.append(Document(page_content=user_text, metadata={"type": "user", "name": name}))
    
    
    # ingestamos datos de Libros e inyectamos autores (Ex 7.4)
    for book_desc in root.findall(XPATH_BOOKS, NAMESPACES):
        title = book_desc.find(XPATH_BOOK_TITLE, NAMESPACES).text
        genres = [g.text for g in book_desc.findall(XPATH_BOOK_GENRE, NAMESPACES) if g.text]
        
        req_level_node = book_desc.find(XPATH_BOOK_REQ_LEVEL, NAMESPACES)
        req_level = req_level_node.text if req_level_node is not None else "Unknown"
        
        author = "Unknown Author"
        if "Dune" in title:
            author = "Frank Herbert"
        elif "Silent Patient" in title:
            author = "Alex Michaelides"
        elif "Hunger Games" in title:
            author = "Suzanne Collins"
            
        book_text = f"Book Title: {title}. Written by Author: {author}. Genres and themes: {', '.join(genres)}. Suitable for required reading level: {req_level}."
        documents.append(Document(page_content=book_text, metadata={"type": "book", "title": title}))
    # Embeddings y almacenar en la Vector DB
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_db = Chroma.from_documents(documents=documents, embedding=embeddings, persist_directory=DB_DIR)

    # prompt de Blindaje (System Prompt) para evitar Alucinaciones y asegurar RAG puro
    prompt_template = """You are an AI assistant integrated into a Semantic Web Book Recommendation System.
    Your answers MUST be based strictly and only on the context provided below.
    If the context does not contain the answer, reply exactly with: "I don't know based on the database."
    Do not use your general pre-trained knowledge under any circumstance.

    Context:
    {context}

    Question: {question}
    Answer:"""
    
    QA_PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

    # config definitiva de la cadena RetrievalQA
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0)
    rag_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_db.as_retriever(search_kwargs={"k": 3}),
        chain_type_kwargs={"prompt": QA_PROMPT}
    )

@app.on_event("startup")
def startup_event():
    load_and_vectorize_rdf()

@app.post("/ask")
def ask_assistant(payload: ChatQuery):
    if not rag_chain:
        raise HTTPException(status_code=500, detail="RAG system core is offline.")
    try:
        result = rag_chain.run(payload.question)
        return {"response": result.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))