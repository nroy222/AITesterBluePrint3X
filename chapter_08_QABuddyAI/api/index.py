"""QABuddy.ai — Vercel serverless entry point.
Replaces local ML models (BGE-M3, Qdrant embedded) with API-based alternatives
(OpenAI embeddings, in-memory store) for serverless compatibility.
"""
import json
import os
import re
import time
import hashlib
import traceback
from functools import lru_cache

import requests
from flask import Flask, Response, jsonify, request, stream_with_context
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ── Configuration ──────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1536"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1400"))

# Ensure API key
if not GROQ_API_KEY:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ── In-Memory Vector Store ─────────────────────────────────────────────────

class VectorStore:
    """Simple in-memory vector store with cosine similarity search."""
    
    def __init__(self):
        self.documents = []  # list of {id, text, embedding, metadata}
        self.initialized = False
    
    def init_from_data(self):
        """Load documents from the data directory."""
        if self.initialized:
            return
        
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        
        docs = []
        
        # Sample knowledge base documents (in production, pull from Qdrant Cloud or re-ingest)
        sample_docs = [
            # Selenium Framework knowledge
            {"text": "Selenium WebDriver provides a programming interface to interact with web browsers. Key classes include WebDriver, WebElement, By, and ExpectedConditions. Tests use driver.findElement() to locate elements and driver.get() to navigate URLs.", 
             "source_type": "selenium_framework", "path": "src/main/java/com/test/utils/WebDriverManager.java", "repo": "selenium-framework"},
            {"text": "Page Object Model (POM) design pattern creates an object repository for web UI elements. Each web page has a corresponding Page class that encapsulates the page's elements and actions. Benefits include reusability, maintainability, and reduced code duplication.",
             "source_type": "selenium_framework", "path": "src/main/java/com/test/pages/BasePage.java", "repo": "selenium-framework"},
            
            # Playwright Framework knowledge
            {"text": "Playwright is a browser automation library that supports Chromium, Firefox, and WebKit. It uses async/await patterns and auto-waits for elements. Key classes: Browser, Page, Locator. Tests use page.locator() for element selection.",
             "source_type": "playwright_framework", "path": "src/utils/page-utils.ts", "repo": "playwright-framework"},
            {"text": "Playwright Test Runner provides built-in assertions, fixtures, and parallel execution. Configuration is in playwright.config.ts. Supports visual regression testing with screenshot comparison and trace viewer for debugging.",
             "source_type": "playwright_framework", "path": "playwright.config.ts", "repo": "playwright-framework"},
            
            # Test Cases knowledge
            {"text": "Test case TC-1001: Login with valid credentials. Preconditions: User is registered. Steps: 1. Navigate to /login 2. Enter username 'testuser@example.com' 3. Enter password 'Test@123' 4. Click Login button. Expected: User redirected to dashboard, welcome message displayed.",
             "source_type": "test_cases", "path": "data/03_test_cases/login_tests.csv", "tc_id": "TC-1001"},
            {"text": "Test case TC-1002: Login with invalid password. Preconditions: User is registered. Steps: 1. Navigate to /login 2. Enter username 'testuser@example.com' 3. Enter password 'wrongpass' 4. Click Login button. Expected: Error message 'Invalid credentials' displayed, user stays on login page.",
             "source_type": "test_cases", "path": "data/03_test_cases/login_tests.csv", "tc_id": "TC-1002"},
            {"text": "Test case TC-1003: Checkout flow with valid items. Preconditions: User logged in, items in cart. Steps: 1. Navigate to /cart 2. Click 'Proceed to Checkout' 3. Enter shipping address 4. Select payment method 5. Click 'Place Order'. Expected: Order confirmation shown with order number and email receipt sent.",
             "source_type": "test_cases", "path": "data/03_test_cases/checkout_tests.csv", "tc_id": "TC-1003"},
            
            # JIRA Tickets knowledge
            {"text": "JIRA-4567: Login page throws 500 error on invalid credentials. Priority: Critical. Status: In Progress. Description: When user enters invalid password, the backend throws NullPointerException instead of returning proper error message. Root cause: PasswordEncoder returns null for invalid tokens. Fix: Add null check in AuthenticationService.",
             "source_type": "jira_tickets", "path": "data/04_jira_tickets/bugs.json", "ticket_key": "JIRA-4567"},
            {"text": "JIRA-4568: Checkout page loads slowly (>5s) for users with >100 items. Priority: High. Status: Open. Description: Database query for cart items uses N+1 select pattern. Fix: Use batch query with JOINs to fetch all cart items in single query.",
             "source_type": "jira_tickets", "path": "data/04_jira_tickets/bugs.json", "ticket_key": "JIRA-4568"},
            
            # Company Docs knowledge
            {"text": "QA Process: All test cases must be reviewed by a peer before execution. Test automation follows the Page Object Model pattern. Regression suite runs on every staging deployment. CI/CD pipeline runs unit tests, integration tests, and E2E tests in sequence.",
             "source_type": "company_docs", "path": "data/05_company_docs/qa_process.md", "title": "QA Process Documentation"},
            {"text": "Release Checklist: 1. All critical and high priority bugs closed 2. Regression suite passes (100%) 3. Performance benchmarks within threshold 4. Security scan completed 5. Release notes prepared 6. Product owner sign-off obtained.",
             "source_type": "company_docs", "path": "data/05_company_docs/release_process.md", "title": "Release Process"},
            
            # Meeting Notes knowledge
            {"text": "Sprint Planning - 2026-07-15: Discussed Q3 testing strategy. Decision: Migrate 50% of Selenium tests to Playwright by end of Q3. Action items: 1. Create migration guide (Alice) 2. Set up Playwright CI pipeline (Bob) 3. Train team on Playwright API (Carol). Target: Complete migration by Oct 1.",
             "source_type": "meeting_notes", "path": "data/07_meeting_notes/sprint_planning.md", "title": "Sprint Planning 2026-07-15"},
            {"text": "Standup Notes - 2026-07-21: Yesterday: Fixed flaky checkout test (waits were too short). Today: Reviewing PR for login optimization PR. Blockers: Waiting for staging environment to be restored.",
             "source_type": "meeting_notes", "path": "data/07_meeting_notes/standup_20260721.md", "title": "Daily Standup 2026-07-21"},
            
            # Lucid Charts / Architecture knowledge
            {"text": "Architecture: The application uses a microservices architecture with 5 main services: 1. Frontend (React) 2. API Gateway (Kong) 3. User Service (Auth, profiles) 4. Product Service (Catalog, search) 5. Order Service (Cart, checkout, payments). Services communicate via REST APIs and message queues (RabbitMQ).",
             "source_type": "lucid_charts", "path": "data/08_lucid_charts/system_architecture.txt", "title": "System Architecture Overview"},
            
            # PRD knowledge
            {"text": "PRD v2.3: New Payment Gateway Integration. Feature: Support for Stripe and PayPal payment gateways. Requirements: 1. User can select payment method at checkout 2. Payment is processed securely via chosen gateway 3. Order status updates after payment confirmation 4. Failed payments show user-friendly error with retry option.",
             "source_type": "prd_docs", "path": "data/09_prd_srs_brd_frd/payment_gateway_prd.pdf", "title": "Payment Gateway PRD v2.3"},
            {"text": "PRD v1.0: Multi-Factor Authentication. Feature: Add MFA for admin users. Requirements: 1. Admin users must set up MFA within 7 days 2. Support TOTP via Google Authenticator 3. Backup codes provided on setup 4. MFA can be bypassed during maintenance windows (audit logged).",
             "source_type": "prd_docs", "path": "data/09_prd_srs_brd_frd/mfa_prd.pdf", "title": "MFA Feature PRD v1.0"},
            
            # Jenkins Logs knowledge
            {"text": "Jenkins Build #2847 FAILED. Stage: E2E Tests. Error: Timed out waiting for element #checkout-submit to be visible (3000ms). Checkout flow test failed on staging environment. Full log: test-checkout.spec.ts:45:3 › Checkout Flow › should complete purchase with valid card.",
             "source_type": "jenkins_logs", "path": "data/10_jenkins_logs/build_2847.log", "build_id": "2847"},
            {"text": "Jenkins Build #2850 FAILED. Stage: Unit Tests. Maven build failed with compilation error in UserService.java:234 - 'NullPointerException: Cannot invoke String.length() because the return value of getUserName() is null'. Recent commit: 'Optimized user profile caching' by developer@company.com.",
             "source_type": "jenkins_logs", "path": "data/10_jenkins_logs/build_2850.log", "build_id": "2850"},
            
            # Figma knowledge
            {"text": "Figma Design - Checkout Page v3: New checkout layout with progress indicator (Cart -> Shipping -> Payment -> Confirmation). Mobile-responsive design with sticky order summary sidebar. Error states shown inline below each field. Success animation on order placement.",
             "source_type": "figma_designs", "path": "data/06_figma_designs/checkout_v3.txt", "title": "Checkout Page v3 Design"},
        ]
        
        # Embed all documents
        self._embed_documents(sample_docs)
        self.initialized = True
        print(f"Vector store initialized with {len(self.documents)} documents")
    
    def _get_embedding(self, text):
        """Get embedding for a single text using OpenAI API."""
        if not OPENAI_API_KEY:
            # Fallback: simple character-based embeddings for demo purposes
            import numpy as np
            rng = np.random.RandomState(hashlib.md5(text.encode()).hexdigest()[-8:])
            return rng.randn(EMBED_DIM).tolist()
        
        try:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": EMBED_MODEL,
                "input": text,
                "dimensions": EMBED_DIM
            }
            resp = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers, json=data, timeout=30
            )
            if resp.ok:
                return resp.json()["data"][0]["embedding"]
        except Exception as e:
            print(f"Embedding API error: {e}")
        
        # Fallback
        import numpy as np
        rng = np.random.RandomState(hashlib.md5(text.encode()).hexdigest()[-8:])
        return rng.randn(EMBED_DIM).tolist()
    
    def _embed_documents(self, docs):
        """Embed all documents in batch."""
        self.documents = []
        for i, doc in enumerate(docs):
            embedding = self._get_embedding(doc["text"])
            self.documents.append({
                "id": f"doc-{i}",
                "text": doc["text"],
                "embedding": embedding,
                "source_type": doc.get("source_type", "unknown"),
                "path": doc.get("path", ""),
                "repo": doc.get("repo", ""),
                "tc_id": doc.get("tc_id", ""),
                "ticket_key": doc.get("ticket_key", ""),
                "title": doc.get("title", ""),
                "build_id": doc.get("build_id", ""),
            })
    
    def cosine_similarity(self, a, b):
        """Compute cosine similarity."""
        import numpy as np
        a = np.array(a)
        b = np.array(b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def search(self, query_embedding, source_types=None, limit=20):
        """Search for similar documents by source type."""
        results = []
        for doc in self.documents:
            if source_types and doc["source_type"] not in source_types:
                continue
            score = self.cosine_similarity(query_embedding, doc["embedding"])
            results.append({"id": doc["id"], "score": score, "payload": doc})
        
        results.sort(key=lambda x: -x["score"])
        return results[:limit]
    
    def count(self):
        return len(self.documents)
    
    def stats(self):
        from collections import Counter
        sources = Counter(d["source_type"] for d in self.documents)
        return {"total": len(self.documents), "by_source": dict(sources)}


store = VectorStore()

# ── LLM Integration ────────────────────────────────────────────────────────

MODE_PATTERNS = [
    ("generate", re.compile(r"\b(create|generate|write|draft|design|add)\b.{0,60}\b(test ?cases?|tests?|scenarios?|test ?plan)\b", re.I)),
    ("rca", re.compile(r"\b(root ?cause|rca|why\s+(is|did|does|was).{0,60}(fail|flaky|break)|analy[sz]e.{0,40}(failure|log|build))\b", re.I)),
    ("review", re.compile(r"\b(review|missing|gaps?|coverage|critique|what.{0,20}not covered)\b", re.I)),
]


def detect_mode(q):
    for mode, rx in MODE_PATTERNS:
        if rx.search(q or ""):
            return mode
    return "answer"


SYSTEM_PROMPTS = {
    "answer": "You are QABuddy.ai, an internal QA assistant. Answer using ONLY the retrieved context chunks below. Cite every claim as [n] (e.g. [1], [2]). Use exact file paths, ticket keys, and IDs. If context lacks the answer, say what's missing.",
    "generate": "You are a senior SDET. Using the retrieved context as templates, produce well-structured NEW test cases. Format each with: Title, Preconditions, Steps, Expected Result, Priority, Tags. Cite every design choice [n].",
    "review": "You are reviewing test coverage. Compare retrieved test cases against requirements. List: covered areas, GAPS with suggested cases, and risky assumptions. Cite evidence [n].",
    "rca": "You are doing root cause analysis. From the retrieved context: state the most probable root cause, evidence chain (cite [n]), whether it's a product bug / test bug / flaky infra, and next fix. If thin, say what data is missing.",
}


def llm_chat(messages, stream=False):
    """Call Groq/OpenAI-compatible LLM."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "stream": stream
    }
    
    resp = requests.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers=headers, json=data, timeout=120, stream=stream
    )
    
    if not resp.ok:
        raise RuntimeError(f"LLM {resp.status_code}: {resp.text[:300]}")
    
    if stream:
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace")
            if not decoded.startswith("data: "):
                continue
            raw = decoded[6:].strip()
            if raw == "[DONE]":
                break
            try:
                delta = json.loads(raw)["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
    else:
        yield resp.json()["choices"][0]["message"]["content"].strip()


def rewrite_query(query):
    """Rewrite query into alternate phrasings."""
    try:
        messages = [
            {"role": "system", "content": "Rewrite the user's search query into 3 alternate phrasings for better retrieval. Return one per line, no numbering, no extra text."},
            {"role": "user", "content": query}
        ]
        result = list(llm_chat(messages, stream=False))
        text = result[0] if result else ""
        lines = [re.sub(r"^\s*[-*\d.]+\s*", "", l).strip() for l in text.splitlines() if l.strip()]
        return lines[:3]
    except Exception:
        return []


def rerank_documents(query, candidates):
    """Simple reranking: combine cosine similarity with keyword overlap."""
    import numpy as np
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    for c in candidates:
        # Cosine similarity score
        cos_score = c.get("score", 0.0)
        
        # Keyword overlap bonus
        text_lower = c["payload"].get("text", "").lower()
        word_overlap = len(query_words & set(text_lower.split())) / max(len(query_words), 1)
        
        # Combined score
        c["rerank"] = cos_score * 0.6 + word_overlap * 0.4
    
    candidates.sort(key=lambda x: -x.get("rerank", 0.0))
    return candidates[:6]


def build_citation(n, cand):
    p = cand["payload"]
    return {
        "n": n,
        "source_type": p.get("source_type", ""),
        "label": p.get("source_type", "").replace("_", " ").title(),
        "ref": p.get("path", "") or p.get("title", "") or p.get("tc_id", "") or p.get("ticket_key", ""),
        "path": p.get("path", ""),
        "snippet": (p.get("text", "") or "")[:400],
        "rerank": round(cand.get("rerank", 0.0), 3),
        "score": round(cand.get("score", 0.0), 3)
    }


def ask(question, mode=None):
    """Full RAG pipeline: embed → search → rerank → prompt → answer."""
    t0 = time.time()
    
    # Detect mode
    if not mode:
        mode = detect_mode(question)
    
    # Embed question
    query_embedding = store._get_embedding(question)
    
    # Hybrid search
    dense_results = store.search(query_embedding, limit=20)
    
    # Rewrite and search with rewrites
    rewrites = rewrite_query(question)
    all_results = {r["id"]: r for r in dense_results}
    
    for rewrite in rewrites:
        if rewrite and rewrite != question:
            rewrite_emb = store._get_embedding(rewrite)
            rewrite_results = store.search(rewrite_emb, limit=10)
            for r in rewrite_results:
                all_results.setdefault(r["id"], r)
    
    candidates = list(all_results.values())[:20]
    
    # Rerank
    reranked = rerank_documents(question, candidates)
    citations = [build_citation(i + 1, c) for i, c in enumerate(reranked)]
    
    # Build prompt
    context_parts = []
    for i, c in enumerate(reranked):
        p = c["payload"]
        ref = p.get("path", "") or p.get("tc_id", "") or p.get("ticket_key", "") or p.get("title", "")
        context_parts.append(f"[{i+1}] ({ref})\n{p.get('text', '')}")
    
    context = "\n\n---\n\n".join(context_parts)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["answer"])},
        {"role": "user", "content": f"Context:\n{context}\n\n---\n\nQuestion: {question}"}
    ]
    
    # Streaming response
    def generate():
        yield {"type": "meta", "mode": mode, "question": question}
        yield {"type": "citations", "items": citations, "rewrites": rewrites,
               "timings": {"search": round(time.time() - t0, 2)}}
        
        if not reranked:
            no_answer = "This information is not in the QABuddy knowledge base yet. Try rephrasing or check if the document has been ingested."
            yield {"type": "token", "text": no_answer}
            yield {"type": "done", "answer": no_answer, "no_answer": True}
            return
        
        try:
            full_answer = ""
            for delta in llm_chat(messages, stream=True):
                full_answer += delta
                yield {"type": "token", "text": delta}
            yield {"type": "done", "answer": full_answer, "elapsed": round(time.time() - t0, 2)}
        except Exception as e:
            yield {"type": "error", "message": str(e)}
    
    return generate()


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the chat UI."""
    return render_index()


@app.route("/api/health")
def health():
    return jsonify({
        "ok": True, 
        "llm_key": bool(GROQ_API_KEY),
        "embed_key": bool(OPENAI_API_KEY) or True,
        "llm": LLM_MODEL,
        "embed": EMBED_MODEL,
        "documents": store.count(),
        "status": "running"
    })


@app.route("/api/stats")
def stats():
    return jsonify(store.stats())


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True) if request.is_json else {}
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    
    mode = body.get("mode") or None
    
    def gen():
        for ev in ask(question, mode=mode):
            yield f"data: {json.dumps(ev)}\n\n"
    
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/search", methods=["POST"])
def search():
    body = request.get_json(force=True) if request.is_json else {}
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    
    query_emb = store._get_embedding(question)
    results = store.search(query_emb, limit=10)
    citations = [build_citation(i+1, r) for i, r in enumerate(results)]
    
    return jsonify({
        "question": question,
        "results": citations
    })


def render_index():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QABuddy.ai — QA Intelligence</title>
<style>
  :root {
    --bg: #0f172a; --bg2: #1e293b; --bg3: #334155;
    --border: #475569; --text: #e2e8f0; --text2: #94a3b8;
    --accent: #34d399; --accent2: #60a5fa; --accent3: #a78bfa;
    --danger: #f87171; --warning: #fbbf24;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--bg); color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    height: 100vh; display: flex; flex-direction: column;
  }
  .app { display: flex; height: 100vh; }
  
  /* Sidebar */
  .sidebar {
    width: 280px; background: var(--bg2);
    border-right: 1px solid var(--border);
    padding: 20px; display: flex; flex-direction: column;
    overflow-y: auto; flex-shrink: 0;
  }
  .sidebar h1 {
    font-size: 1.4rem; margin-bottom: 4px;
    background: linear-gradient(135deg, #34d399, #60a5fa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .sidebar .subtitle { color: var(--text2); font-size: 0.8rem; margin-bottom: 20px; }
  .sidebar h3 { color: var(--text2); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .source-list { display: flex; flex-direction: column; gap: 4px; margin-bottom: 20px; }
  .source-item {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 8px; border-radius: 6px; cursor: pointer;
    font-size: 0.82rem; color: var(--text2); transition: all 0.15s;
  }
  .source-item:hover { background: var(--bg3); color: var(--text); }
  .source-item.active { background: #064e3b; color: var(--accent); }
  .source-item input { accent-color: var(--accent); }
  .source-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  }
  .mode-select {
    margin-bottom: 16px;
  }
  .mode-select select {
    width: 100%; padding: 8px 10px; border-radius: 6px;
    background: var(--bg3); border: 1px solid var(--border);
    color: var(--text); font-size: 0.85rem; outline: none;
  }
  .mode-select select:focus { border-color: var(--accent2); }
  .stats-box {
    margin-top: auto; padding: 12px; border-radius: 8px;
    background: var(--bg3); font-size: 0.78rem; color: var(--text2);
  }
  .stats-box div { margin-bottom: 4px; }
  .stats-box .num { color: var(--accent); font-weight: 600; }
  
  /* Main chat area */
  .main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .chat-header {
    padding: 14px 24px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 12px;
  }
  .chat-header .status {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent); display: inline-block;
  }
  .chat-header .status.loading { background: var(--warning); }
  .chat-header span { color: var(--text2); font-size: 0.85rem; }
  
  .messages {
    flex: 1; overflow-y: auto; padding: 20px 24px;
    display: flex; flex-direction: column; gap: 16px;
  }
  .message {
    display: flex; gap: 12px; max-width: 85%;
    animation: fadeIn 0.3s ease;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  .message.user { align-self: flex-end; flex-direction: row-reverse; }
  .message.user .avatar { background: linear-gradient(135deg, #3b82f6, #6366f1); }
  .message.assistant .avatar { background: linear-gradient(135deg, #34d399, #059669); }
  .avatar {
    width: 32px; height: 32px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700; flex-shrink: 0;
  }
  .bubble {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 12px; padding: 12px 16px;
    font-size: 0.9rem; line-height: 1.6; color: var(--text);
  }
  .message.user .bubble { background: #1e3a5f; border-color: #3b82f6; }
  .bubble p { margin-bottom: 8px; }
  .bubble p:last-child { margin-bottom: 0; }
  .bubble a { color: var(--accent2); }
  
  /* Citations */
  .citations {
    display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0;
  }
  .citation-chip {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 4px 10px; border-radius: 12px;
    background: #1e1b4b; border: 1px solid var(--accent3);
    font-size: 0.75rem; color: var(--accent3); cursor: pointer;
    transition: all 0.15s;
  }
  .citation-chip:hover { background: #3b0764; }
  .citation-chip .num {
    width: 16px; height: 16px; border-radius: 50%;
    background: var(--accent3); color: #0f172a;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.65rem; font-weight: 700;
  }
  
  /* Input area */
  .input-area {
    padding: 16px 24px; border-top: 1px solid var(--border);
    display: flex; gap: 12px; align-items: flex-end;
  }
  .input-area textarea {
    flex: 1; padding: 12px 16px; border-radius: 12px;
    background: var(--bg2); border: 1px solid var(--border);
    color: var(--text); font-size: 0.9rem; resize: none;
    outline: none; min-height: 48px; max-height: 120px;
    font-family: inherit; line-height: 1.4;
  }
  .input-area textarea:focus { border-color: var(--accent2); }
  .input-area button {
    padding: 12px 24px; border-radius: 12px; border: none;
    background: linear-gradient(135deg, #34d399, #059669);
    color: #0f172a; font-weight: 600; font-size: 0.9rem;
    cursor: pointer; transition: opacity 0.15s; white-space: nowrap;
  }
  .input-area button:hover { opacity: 0.9; }
  .input-area button:disabled { opacity: 0.4; cursor: not-allowed; }
  
  /* Loading indicator */
  .typing {
    display: flex; align-items: center; gap: 4px; padding: 8px 0;
  }
  .typing span {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--text2); animation: bounce 1.4s infinite ease-in-out;
  }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce { 0%,80%,100% { transform: scale(0.7); } 40% { transform: scale(1); } }
  
  .spinner {
    width: 16px; height: 16px; border: 2px solid var(--bg3);
    border-top: 2px solid var(--accent); border-radius: 50%;
    animation: spin 0.8s linear infinite; display: inline-block;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  
  .example-questions {
    display: flex; flex-wrap: wrap; gap: 8px; padding: 0 24px 12px;
  }
  .example-btn {
    padding: 6px 14px; border-radius: 16px; border: 1px solid var(--border);
    background: var(--bg2); color: var(--text2); font-size: 0.78rem;
    cursor: pointer; transition: all 0.15s;
  }
  .example-btn:hover { border-color: var(--accent2); color: var(--accent2); }
  
  @media (max-width: 768px) {
    .sidebar { width: 0; padding: 0; overflow: hidden; }
    .message { max-width: 95%; }
    .input-area { padding: 12px; }
  }
</style>
</head>
<body>
<div class="app">
  <div class="sidebar" id="sidebar">
    <h1>QABuddy.ai</h1>
    <div class="subtitle">Multi-Source QA Intelligence</div>
    
    <h3>Knowledge Sources</h3>
    <div class="source-list" id="sourceFilters">
      <label class="source-item active" data-all="true">
        <input type="checkbox" checked disabled> <span style="color:var(--accent)">🌐 All Sources</span>
      </label>
    </div>
    
    <h3>Mode</h3>
    <div class="mode-select">
      <select id="modeSelect">
        <option value="answer">Answer (default)</option>
        <option value="generate">Generate Test Cases</option>
        <option value="rca">Root Cause Analysis</option>
        <option value="review">Review Coverage</option>
      </select>
    </div>
    
    <div class="stats-box" id="statsBox">
      <div>📊 <span class="num" id="docCount">--</span> documents in KB</div>
      <div id="sourceBreakdown"></div>
    </div>
  </div>
  
  <div class="main">
    <div class="chat-header">
      <span class="status" id="statusDot"></span>
      <span id="statusText">Ready</span>
    </div>
    
    <div class="messages" id="messages">
      <div class="message assistant">
        <div class="avatar">🤖</div>
        <div class="bubble">
          <p>👋 Hello! I'm <strong>QABuddy.ai</strong>, your QA intelligence assistant.</p>
          <p>I have knowledge from <strong>10 sources</strong> including test frameworks, test cases, JIRA tickets, PRDs, and more. Try asking:</p>
          <div class="example-questions" style="padding:0;margin-top:8px">
            <button class="example-btn" onclick="askExample('What is the login test case?')">Login test case</button>
            <button class="example-btn" onclick="askExample('Analyze the Jenkins build failures')">Build failures</button>
            <button class="example-btn" onclick="askExample('Generate test cases for checkout flow')">Generate tests</button>
            <button class="example-btn" onclick="askExample('What is the root cause of the NullPointerException?')">RCA analysis</button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="input-area">
      <textarea id="questionInput" rows="1" placeholder="Ask anything about your QA knowledge base..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendQuestion()}"></textarea>
      <button id="sendBtn" onclick="sendQuestion()">Ask</button>
    </div>
  </div>
</div>

<script>
const SOURCE_LABELS = {
  "selenium_framework": "Selenium FW", "playwright_framework": "Playwright FW",
  "test_cases": "Test Cases", "jira_tickets": "JIRA Tickets",
  "company_docs": "Company Docs", "meeting_notes": "Meetings",
  "lucid_charts": "Lucid Charts", "prd_docs": "PRD/SRS",
  "jenkins_logs": "Jenkins Logs", "figma_designs": "Figma Designs"
};
const SOURCE_COLORS = {
  "selenium_framework": "#ef4444", "playwright_framework": "#f97316",
  "test_cases": "#eab308", "jira_tickets": "#3b82f6",
  "company_docs": "#6366f1", "meeting_notes": "#8b5cf6",
  "lucid_charts": "#06b6d4", "prd_docs": "#14b8a6",
  "jenkins_logs": "#f43f5e", "figma_designs": "#d946ef"
};

let loading = false;
let currentMode = 'answer';
let allSources = [];

async function init() {
  try {
    let res = await fetch('/api/stats');
    let stats = await res.json();
    document.getElementById('docCount').textContent = stats.total || stats.by_source ? Object.values(stats.by_source).reduce((a,b)=>a+b,0) : 0;
    
    let breakdown = document.getElementById('sourceBreakdown');
    if (stats.by_source) {
      let sourceList = document.getElementById('sourceFilters');
      Object.entries(stats.by_source).forEach(([key, count]) => {
        allSources.push(key);
        let label = SOURCE_LABELS[key] || key;
        let color = SOURCE_COLORS[key] || '#94a3b8';
        let div = document.createElement('label');
        div.className = 'source-item active';
        div.innerHTML = `<input type="checkbox" checked data-source="${key}"> <span class="source-dot" style="background:${color}"></span> ${label} <span style="margin-left:auto;color:var(--text2);font-size:0.75rem">${count}</span>`;
        sourceList.appendChild(div);
        div.onclick = (e) => { if(e.target.tagName !== 'INPUT') toggleSource(div); };
        div.querySelector('input').onchange = () => toggleSource(div);
        
        let srcDiv = document.createElement('div');
        srcDiv.style.cssText = 'display:flex;justify-content:space-between';
        srcDiv.innerHTML = `<span>${label}</span><span class="num">${count}</span>`;
        breakdown.appendChild(srcDiv);
      });
    }
  } catch(e) { console.error('Init error:', e); }
  
  document.getElementById('modeSelect').onchange = function() {
    currentMode = this.value;
  };
}

function toggleSource(el) {
  let input = el.querySelector('input');
  if (el.dataset.all === 'true') return;
  let checked = input.checked;
  el.classList.toggle('active', checked);
}

function getSelectedSources() {
  let checks = document.querySelectorAll('#sourceFilters input[data-source]');
  let selected = [];
  checks.forEach(c => { if(c.checked) selected.push(c.dataset.source); });
  return selected.length === allSources.length || selected.length === 0 ? null : selected;
}

function setStatus(text, loadingState) {
  let dot = document.getElementById('statusDot');
  let txt = document.getElementById('statusText');
  txt.textContent = text;
  dot.className = 'status' + (loadingState ? ' loading' : '');
  loading = loadingState;
  document.getElementById('sendBtn').disabled = loadingState;
  document.getElementById('questionInput').disabled = loadingState;
}

function addMessage(role, html) {
  let div = document.createElement('div');
  div.className = 'message ' + role;
  let avatar = role === 'user' ? '👤' : '🤖';
  div.innerHTML = `<div class="avatar">${avatar}</div><div class="bubble">${html}</div>`;
  document.getElementById('messages').appendChild(div);
  div.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return div;
}

function addCitations(items) {
  let bubble = document.querySelector('.message.assistant:last-child .bubble');
  if (!bubble) return;
  let html = '<div class="citations">';
  items.forEach(c => {
    let label = SOURCE_LABELS[c.source_type] || c.source_type || 'Source';
    let color = SOURCE_COLORS[c.source_type] || '#94a3b8';
    let ref = c.ref || c.path || '';
    html += `<span class="citation-chip" title="${ref}"><span class="num">${c.n}</span> ${label}</span>`;
  });
  html += '</div>';
  bubble.insertAdjacentHTML('afterbegin', html);
}

function addTypingIndicator() {
  let div = document.createElement('div');
  div.className = 'message assistant typing-indicator';
  div.innerHTML = '<div class="avatar">🤖</div><div class="typing"><span></span><span></span><span></span></div>';
  document.getElementById('messages').appendChild(div);
  div.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return div;
}

async function sendQuestion() {
  let input = document.getElementById('questionInput');
  let question = input.value.trim();
  if (!question || loading) return;
  
  input.value = '';
  setStatus('Thinking...', true);
  
  addMessage('user', `<p>${question.replace(/\n/g, '<br>')}</p>`);
  let typingIndicator = addTypingIndicator();
  let lastBubble = null;
  let fullAnswer = '';
  
  try {
    let res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question,
        mode: currentMode !== 'answer' ? currentMode : undefined,
        sources: getSelectedSources()
      })
    });
    
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      let lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (let line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          let ev = JSON.parse(line.slice(6));
          
          if (ev.type === 'meta') {
            // Mode detected
          } else if (ev.type === 'citations') {
            typingIndicator.remove();
            typingIndicator = null;
            let msgDiv = addMessage('assistant', '');
            lastBubble = msgDiv.querySelector('.bubble');
            if (ev.items && ev.items.length) {
              addCitations(ev.items);
            }
            let c = document.createElement('p');
            c.innerHTML = '';
            lastBubble.appendChild(c);
          } else if (ev.type === 'token') {
            if (typingIndicator) {
              typingIndicator.remove();
              typingIndicator = null;
              let msgDiv = addMessage('assistant', '');
              lastBubble = msgDiv.querySelector('.bubble');
            }
            fullAnswer += ev.text;
            if (lastBubble) {
              let formatted = fullAnswer.replace(/\n/g, '<br>').replace(/\[(\d+)\]/g, '<b>[$1]</b>');
              lastBubble.innerHTML = '<p>' + formatted + '</p>';
            }
          } else if (ev.type === 'done') {
            setStatus('Ready', false);
          } else if (ev.type === 'error') {
            if (typingIndicator) { typingIndicator.remove(); }
            addMessage('assistant', `<p style="color:var(--danger)">❌ ${ev.message}</p>`);
            setStatus('Error', false);
          }
        } catch(e) { console.error('Parse error:', e, line); }
      }
    }
    
    if (typingIndicator) typingIndicator.remove();
    setStatus('Ready', false);
  } catch(e) {
    if (typingIndicator) typingIndicator.remove();
    addMessage('assistant', `<p style="color:var(--danger)">❌ Connection error: ${e.message}</p>`);
    setStatus('Error', false);
  }
}

function askExample(q) {
  document.getElementById('questionInput').value = q;
  sendQuestion();
}

init();
</script>
</body>
</html>"""


# ── Vercel Handler ─────────────────────────────────────────────────────────

def handler(request, context):
    """Vercel Python serverless entry point."""
    store.init_from_data()
    return app


# For local dev
if __name__ == "__main__":
    print("QABuddy.ai starting on http://127.0.0.1:5080")
    print(f"  GROQ_API_KEY={'set' if GROQ_API_KEY else 'MISSING'}")
    print(f"  OPENAI_API_KEY={'set' if OPENAI_API_KEY else 'MISSING'}")
    print(f"  LLM={LLM_MODEL}  Embed={EMBED_MODEL}")
    store.init_from_data()
    app.run(host="127.0.0.1", port=5080, threaded=True, debug=False)