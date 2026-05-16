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
    NAMESPACES, XPATH_INDIVIDUALS, XPATH_TYPE, XPATH_NAME, XPATH_TITLE,
    XPATH_AUTHOR, XPATH_GENRE, XPATH_READING_LEVEL, XPATH_REQUIRED_LEVEL, XPATH_PREFERRED_THEME
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
RDF_PATH = "../ontology/book_ontology.rdf"
rag_chain = None

def load_and_vectorize_rdf():
    global rag_chain
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("ERROR: La variable de entorno GOOGLE_API_KEY o GEMINI_API_KEY no está configurada en Windows.")

    os.environ["GOOGLE_API_KEY"] = api_key

    # parsear el archivo RDF/XML
    try:
        tree = ET.parse(RDF_PATH)
        root = tree.getroot()
    except Exception as e:
        raise ValueError(f"Error al abrir el archivo RDF: {str(e)}")
    
    documents = []

    authors_map = {}
    for ind in root.findall(XPATH_INDIVIDUALS, NAMESPACES):
        type_node = ind.find(XPATH_TYPE, NAMESPACES)
        if type_node is not None:
            resource = type_node.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource")
            if resource and resource.endswith("#Author"):
                uri = ind.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
                name_node = ind.find(XPATH_NAME, NAMESPACES)
                if uri and name_node is not None:
                    authors_map[uri] = name_node.text

    # ingestamos datos de Usuarios y libros (Ex 7.3)
    for ind in root.findall(XPATH_INDIVIDUALS, NAMESPACES):
        type_node = ind.find(XPATH_TYPE, NAMESPACES)
        if type_node is None:
            continue
        resource = type_node.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource")
        if not resource:
            continue
        
        # USUARIOS
        if resource.endswith("#User"):
            name_node = ind.find(XPATH_NAME, NAMESPACES)
            name = name_node.text if name_node is not None else "Unknown"
            
            lvl_node = ind.find(XPATH_READING_LEVEL, NAMESPACES)
            lvl_res = lvl_node.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource") if lvl_node is not None else ""
            level = lvl_res.split("#")[-1] if "#" in lvl_res else "Unknown"
            
            theme_node = ind.find(XPATH_PREFERRED_THEME, NAMESPACES)
            theme_res = theme_node.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource") if theme_node is not None else ""
            theme = theme_res.split("#")[-1] if "#" in theme_res else "Unknown"
            
            user_text = f"User profile: {name}. Has a reading level of {level} and prefers the theme or genre {theme}."
            documents.append(Document(page_content=user_text, metadata={"type": "user", "name": name}))
        
        # LIBROS
        elif resource.endswith("#Book"):
            title_node = ind.find(XPATH_TITLE, NAMESPACES)
            title = title_node.text if title_node is not None else "Unknown"
            
            genres = []
            for g_node in ind.findall(XPATH_GENRE, NAMESPACES):
                g_res = g_node.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource")
                if g_res:
                    genres.append(g_res.split("#")[-1])
            
            lvl_node = ind.find(XPATH_REQUIRED_LEVEL, NAMESPACES)
            lvl_res = lvl_node.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource") if lvl_node is not None else ""
            req_level = lvl_res.split("#")[-1] if "#" in lvl_res else "Unknown"
            
            # RESOLUCIÓN SEMÁNTICA: Cruzamos la URI del autor con nuestro mapa de memoria
            author_node = ind.find(XPATH_AUTHOR, NAMESPACES)
            author_res = author_node.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource") if author_node is not None else ""
            author = authors_map.get(author_res, "Unknown Author")
            
            book_text = f"Book Title: {title}. Written by Author: {author}. Genres and themes: {', '.join(genres)}. Suitable for required reading level: {req_level}."
            documents.append(Document(page_content=book_text, metadata={"type": "book", "title": title}))


    # Embeddings y almacenar en la Vector DB
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2-preview")
    if os.path.exists(DB_DIR) and os.listdir(DB_DIR):
        # Esto reduce las llamadas a la API a CERO, mitigando por completo el Error 429
        vector_db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    else:
        # Si la base de datos no existe (primera ejecución), se calcula y se guarda en disco
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
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
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
        response_dict = rag_chain.invoke(payload.question)
        return {"response": response_dict["result"].strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))