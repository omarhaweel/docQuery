"""
RAG pipeline with vector store and conversational agent.

Flow: load all PDFs → chunk text → embed & index in one FAISS store → RAG QA chain
→ agent with memory → interactive Q&A. The LLM can search across every document.
"""

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_classic.chains import RetrievalQA
from langchain_openai import ChatOpenAI




# -----------------------------------------------------------------------------
# 1. CONFIGURATION
# -----------------------------------------------------------------------------
load_dotenv()

DOCUMENTS_DIR = "Documents"
if os.path.isdir(DOCUMENTS_DIR):
    paths = []
    for path in Path(DOCUMENTS_DIR).rglob("*.pdf"):
        paths.append(str(path))
    DOCUMENT_PATHS = paths
else:
    DOCUMENT_PATHS = []



# larger chunks = more context
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
LLM_MODEL = "gpt-4o"
# Single vector store for all documents.
VECTORSTORE_DIR = "./vectorstore"

# -----------------------------------------------------------------------------
# 2. LOAD DOCUMENTS
# -----------------------------------------------------------------------------
documents = []
for path in DOCUMENT_PATHS:
    loader = PyPDFLoader(path)
    docs = loader.load()
    for d in docs:
        d.metadata["source"] = path
    documents.extend(docs)

# -----------------------------------------------------------------------------
# 3. EMBEDDINGS
# -----------------------------------------------------------------------------

embeddings = OpenAIEmbeddings()

# -----------------------------------------------------------------------------
# 4. SPLIT INTO CHUNKS AND BUILD VECTOR STORE
# -----------------------------------------------------------------------------

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)
# One chunk list from all documents so the retriever searches across every doc.
chunks = splitter.split_documents(documents)

# Manifest file: which documents were indexed. Rebuild if the document folder changes.
MANIFEST_FILE = os.path.join(VECTORSTORE_DIR, ".documents.txt")


def _normalized_document_list():
    """Sorted, normalized paths for comparison."""
    return sorted(os.path.abspath(p) for p in DOCUMENT_PATHS)

def _index_matches_current_documents():
    """True if the saved index was built from the same document set as DOCUMENT_PATHS."""
    if not os.path.isfile(MANIFEST_FILE):
        return False
    try:
        with open(MANIFEST_FILE, "r") as f:
            saved = sorted(line.strip() for line in f if line.strip())
    except OSError:
        return False
    current = _normalized_document_list()
    return saved == current

# Load from disk only if the index exists AND was built from the same documents.
if os.path.isdir(VECTORSTORE_DIR) and _index_matches_current_documents():
    vectorstore = FAISS.load_local(VECTORSTORE_DIR, embeddings, allow_dangerous_deserialization=True)
else:
    if os.path.isdir(VECTORSTORE_DIR):
        shutil.rmtree(VECTORSTORE_DIR)
    os.makedirs(VECTORSTORE_DIR, exist_ok=True)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(VECTORSTORE_DIR)
    with open(MANIFEST_FILE, "w") as f:
        for p in _normalized_document_list():
            f.write(p + "\n")

# -----------------------------------------------------------------------------
# 5. RAG QA CHAIN (grounded in retrieved documents only)
# -----------------------------------------------------------------------------

# Base retriever: many chunks by similarity so details are not missed.
_base_retriever = vectorstore.as_retriever(search_kwargs={"k": 20})

# LLM used for both the RAG chain and the agent.
llm = ChatOpenAI(model=LLM_MODEL, temperature=0.3)

# Multi-query retriever: generates alternative phrasings (e.g. "søkestrategi", "plan jobb")
# and merges results so we find the right passage even when wording differs from the document.
from langchain_classic.retrievers import MultiQueryRetriever
retriever = MultiQueryRetriever.from_llm(retriever=_base_retriever, llm=llm, include_original=True)

# Strict grounding prompt: answer ONLY from the context; say when not found.
RAG_SYSTEM_PROMPT = """You must answer the user's question using ONLY the following context from their documents. Do not use outside knowledge.
- If the answer is in the context, answer in a clear, concise way and stay faithful to the text.
- If the answer is NOT in the context, say: "I don't have that information in the documents."
Do not make up or assume anything that is not in the context.

Context from documents:
{context}"""

rag_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(RAG_SYSTEM_PROMPT),
    HumanMessagePromptTemplate.from_template("{question}"),
])

# "stuff" chain with custom prompt so the model is grounded in retrieved chunks only.
qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    chain_type_kwargs={"prompt": rag_prompt},
    return_source_documents=True,
)

# -----------------------------------------------------------------------------
# 6. AGENT WITH RAG TOOL AND MEMORY
# -----------------------------------------------------------------------------
from langchain_core.exceptions import OutputParserException
from langchain_classic.agents import initialize_agent, Tool
from langchain_classic.memory import ConversationBufferMemory


def _handle_parsing_error(e: OutputParserException) -> str:
    """When the agent outputs a normal reply without 'Final Answer:', tell it to use that as Final Answer."""
    msg = str(e)
    if "Could not parse LLM output:" in msg and "`" in msg:
        start = msg.find("`") + 1
        end = msg.rfind("`")
        if end > start:
            llm_reply = msg[start:end].strip()
            return f"Use that as your reply. Output exactly this line: Final Answer: {llm_reply}"
    return "Output exactly one line: Final Answer: <repeat your reply to the user in one sentence>"

# Tool must return a string; RetrievalQA.invoke returns a dict with "result" key.
def rag_query(query: str) -> str:
    return qa.invoke({"query": query})["result"]

def irrelevant_questions(query: str) -> str:
    model_response = llm.invoke(query)
    return model_response.content

tools = [
    Tool(
        name="rag_chain",
        func=rag_query,
        description=(
            "Use this to READ the documents and answer. You have no other way to read document content. "
            "Use it for ANY question about what is IN the documents: details, names, dates, facts, content, summaries. "
            "Always use rag_chain when the user asks about something that might be in their documents. "
            "Do NOT use for: greetings, thanks, short replies (respond directly), or 'which documents do you have?' (use list_documents)."
        ),
    ),
    Tool(
        name="irrelevant_questions",
        func=irrelevant_questions,
        description=(
            "Use ONLY for questions that are clearly NOT about the documents at all (e.g. general knowledge, math, news). "
            "If the user might be asking about something in their documents (e.g. a person, date, detail), use rag_chain instead."
        ),
    ),
] 

# Memory keeps chat history so the agent can refer to earlier turns.
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=False,  # zero-shot-react expects string history
)

# Single agent instance: RAG tool + memory, used for the whole conversation.
agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    memory=memory,
    verbose=True,
    handle_parsing_errors=_handle_parsing_error,
    max_iterations=6,
    early_stopping_method="force",
)

# -----------------------------------------------------------------------------
# 7. RUN PIPELINE (one-off) AND INTERACTIVE LOOP
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Optional: run one query without the agent to test RAG only.
    test_query = "Hva er Nokut?"
    direct_result = qa.invoke({"query": test_query})
    print("RAG only:", direct_result["result"], "\n")

    # Interactive loop: agent uses RAG tool and memory.
    print("Ask about the documents (type 'quit' to exit).\n")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        result = agent.invoke({"input": user_input})
        print("Agent:", result["output"], "\n")
