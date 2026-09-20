"""Streamlit UI for comparing three retrieval strategies side by side."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from html import escape
import json
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

import streamlit as st
from dotenv import load_dotenv


load_dotenv()

st.set_page_config(
    page_title="RAG Compare — Đối chiếu 3 pipeline",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TOP_K = 5
BENCHMARK_RESULTS = Path(__file__).parent / "group_project" / "evaluation" / "benchmark_results.json"


GLOBAL_CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;650;700&display=swap');

:root {
  --bg: #f2f7f3;
  --panel: rgba(255, 255, 255, .9);
  --panel-strong: rgba(255, 255, 255, .98);
  --line: rgba(30, 67, 48, .14);
  --line-soft: rgba(30, 67, 48, .085);
  --text: #17231d;
  --muted: #65766d;
  --green: #16784a;
  --mint: #45bd7b;
  --orange: #e9854d;
  --purple: #7765da;
  --cyan: #168f8a;
}

* { box-sizing: border-box; }
html, body, [class*="css"] { font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
body { color: var(--text); }

[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 8% -8%, rgba(111, 220, 159, .32), transparent 34rem),
    radial-gradient(circle at 96% 9%, rgba(176, 160, 246, .28), transparent 31rem),
    radial-gradient(circle at 54% 64%, rgba(115, 205, 162, .12), transparent 36rem),
    linear-gradient(180deg, #f8fcf9 0%, var(--bg) 44%, #eaf2ed 100%);
}

[data-testid="stAppViewContainer"]::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: .06;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 140 140' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.11'/%3E%3C/svg%3E");
  mix-blend-mode: soft-light;
}

[data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }
[data-testid="stMain"] { overflow: visible; }
.block-container {
  width: min(1460px, 100%);
  max-width: 1460px;
  padding: 1.35rem 2rem 9.2rem !important;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  margin-bottom: clamp(2.4rem, 6vh, 5rem);
}
.brand { display: flex; align-items: center; gap: 11px; }
.brand-mark {
  width: 31px;
  height: 31px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  color: #0b120d;
  background: linear-gradient(145deg, #d7ffe4, #74d89e);
  box-shadow: 0 9px 30px rgba(82, 220, 143, .34), inset 0 1px 0 rgba(255,255,255,.82);
}
.brand-mark svg { width: 18px; height: 18px; }
.brand-copy strong { display: block; color: #16231c; font-size: 14px; line-height: 1.1; letter-spacing: -.025em; }
.brand-copy span { color: var(--muted); font-size: 9px; letter-spacing: .18em; text-transform: uppercase; }
.corpus-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: #506159;
  background: rgba(255, 255, 255, .74);
  box-shadow: 0 8px 28px rgba(40, 92, 62, .08);
  font-size: 11px;
}
.corpus-chip i { width: 6px; height: 6px; border-radius: 50%; background: var(--mint); box-shadow: 0 0 12px rgba(140,230,176,.7); }

.hero { max-width: 760px; margin: 0 auto clamp(2rem, 4.8vh, 3.5rem); text-align: center; }
.eyebrow {
  color: #287b50;
  font-size: 10px;
  font-weight: 650;
  letter-spacing: .19em;
  text-transform: uppercase;
}
.hero h1 {
  max-width: 760px;
  margin: 13px auto 12px;
  color: #14231b;
  font-size: clamp(34px, 4.05vw, 62px);
  font-weight: 500;
  letter-spacing: -.055em;
  line-height: 1.02;
}
.hero p {
  max-width: 610px;
  margin: 0 auto;
  color: #64756c;
  font-size: clamp(12px, 1.05vw, 15px);
  line-height: 1.65;
}

.results-bar {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin: 0 0 13px;
}
.results-title { color: #24352c; font-size: 12px; font-weight: 600; letter-spacing: -.01em; }
.results-note { margin-top: 4px; color: #718078; font-size: 10px; }

div[data-testid="stButton"] { width: fit-content; margin-left: auto; }
div[data-testid="stButton"] > button {
  min-height: 34px;
  padding: 0 13px;
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
  color: #35483e !important;
  background: rgba(255,255,255,.82) !important;
  box-shadow: 0 8px 24px rgba(35,76,52,.07) !important;
  font-size: 11px !important;
  transition: .18s ease !important;
}
div[data-testid="stButton"] > button:hover {
  color: #17653f !important;
  border-color: rgba(33,132,78,.26) !important;
  background: rgba(73,190,124,.1) !important;
  transform: translateY(-1px);
}

[data-testid="stHorizontalBlock"] { gap: 12px; align-items: stretch; }
[data-testid="column"] { min-width: 0; }

.method-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 430px;
  height: 100%;
  overflow: hidden;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: linear-gradient(165deg, rgba(255,255,255,.97), rgba(245,250,247,.94));
  box-shadow: 0 22px 55px rgba(42,82,58,.11), inset 0 1px 0 rgba(255,255,255,.95);
  backdrop-filter: blur(20px);
}
.method-card::after {
  content: "";
  position: absolute;
  top: -80px;
  right: -75px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  opacity: .13;
  filter: blur(6px);
  background: var(--accent);
}
.method-head { position: relative; z-index: 1; display: flex; justify-content: space-between; gap: 12px; }
.method-id { display: flex; gap: 11px; align-items: center; min-width: 0; }
.method-icon {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
  border-radius: 11px;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 9%, transparent);
}
.method-icon svg { width: 17px; height: 17px; }
.method-name { color: #1d2c24; font-size: 13px; font-weight: 650; letter-spacing: -.02em; line-height: 1.25; }
.method-stack { margin-top: 3px; color: #77877e; font-size: 8px; font-weight: 650; letter-spacing: .13em; text-transform: uppercase; }
.status-pill {
  height: fit-content;
  white-space: nowrap;
  padding: 5px 8px;
  border: 1px solid var(--line-soft);
  border-radius: 99px;
  color: #6c7c73;
  background: rgba(39,91,60,.045);
  font-size: 8px;
  font-weight: 650;
  letter-spacing: .09em;
  text-transform: uppercase;
}
.status-pill.live { color: #187044; border-color: rgba(39,145,82,.18); background: rgba(63,185,113,.09); }
.status-pill.error { color: #f3b28f; border-color: rgba(242,161,111,.18); background: rgba(242,161,111,.07); }
.method-divider { height: 1px; margin: 17px 0; background: linear-gradient(90deg, var(--line), transparent); }
.empty-state { display: flex; flex: 1; flex-direction: column; justify-content: space-between; }
.empty-copy { max-width: 29ch; color: #596b61; font-size: 11px; line-height: 1.65; }
.empty-visual { display: grid; gap: 8px; margin-top: 30px; }
.empty-line { height: 8px; border-radius: 8px; background: rgba(35,79,52,.075); }
.empty-line:nth-child(2) { width: 86%; }
.empty-line:nth-child(3) { width: 62%; }
.card-foot {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 22px;
  padding-top: 13px;
  border-top: 1px solid var(--line-soft);
  color: #718178;
  font-size: 9px;
}
.answer-label { color: #728279; font-size: 8px; font-weight: 650; letter-spacing: .14em; text-transform: uppercase; }
.answer-text { margin-top: 11px; color: #283a30; font-size: 11.25px; line-height: 1.72; }
.answer-text p + p { margin-top: 9px; }
.answer-error { margin-top: 11px; color: #dba78b; font-size: 10.5px; line-height: 1.6; }
.stat-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; margin-top: 17px; }
.mini-stat { padding: 9px 8px; border: 1px solid var(--line-soft); border-radius: 10px; background: rgba(39,91,60,.035); }
.mini-stat strong { display: block; color: #30443a; font-size: 10px; font-weight: 600; }
.mini-stat span { display: block; margin-top: 3px; color: #7b8b82; font-size: 7.5px; letter-spacing: .08em; text-transform: uppercase; }
.source-list { margin-top: 13px; border-top: 1px solid var(--line-soft); }
.source-list details { padding-top: 12px; }
.source-list summary { cursor: pointer; list-style: none; color: #617269; font-size: 9.5px; user-select: none; }
.source-list summary::-webkit-details-marker { display: none; }
.source-list summary::after { content: "+"; float: right; color: #69726d; font-size: 13px; }
.source-list details[open] summary::after { content: "−"; }
.source-item { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,.045); }
.source-item:last-child { border-bottom: 0; }
.source-rank { color: var(--accent); font-size: 8px; font-weight: 650; }
.source-title { display: block; margin-top: 3px; color: #31463a; font-size: 9.5px; line-height: 1.4; text-decoration: none; }
a.source-title:hover { color: #147044; }
.source-meta { margin-top: 3px; color: #606964; font-size: 8px; line-height: 1.45; }
.query-strip {
  margin-bottom: 12px;
  padding: 11px 14px;
  border: 1px solid var(--line-soft);
  border-radius: 12px;
  color: #40534a;
  background: rgba(255,255,255,.72);
  font-size: 10.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.query-strip span { margin-right: 8px; color: #69726d; font-size: 8px; font-weight: 650; letter-spacing: .11em; text-transform: uppercase; }

[data-testid="stBottom"] {
  background: linear-gradient(180deg, transparent, rgba(238,246,241,.94) 26%, #edf4ef 64%) !important;
  padding: 1.2rem 0 max(1.35rem, env(safe-area-inset-bottom)) !important;
}
[data-testid="stBottom"] > div { width: min(940px, calc(100vw - 2rem)); margin: 0 auto; }
[data-testid="stChatInput"] {
  border: 1px solid rgba(31,89,56,.18) !important;
  border-radius: 18px !important;
  background: rgba(255,255,255,.98) !important;
  box-shadow: 0 18px 55px rgba(38,76,53,.16), inset 0 1px 0 rgba(255,255,255,.95) !important;
  backdrop-filter: blur(24px);
}
[data-testid="stChatInput"] textarea { color: #25382e !important; font-size: 12px !important; caret-color: #16814d; }
[data-testid="stChatInput"] textarea::placeholder { color: #87968e !important; }
[data-testid="stChatInput"] button { color: #0b110d !important; background: linear-gradient(145deg, #cef9dc, #75d99e) !important; border-radius: 11px !important; }

[data-testid="stSpinner"] { color: #9caaa1; }
[data-testid="stDialog"] > div {
  width: min(1040px, calc(100vw - 2rem));
  max-width: 1040px !important;
}
section[role="dialog"] {
  width: 100%;
  max-width: none !important;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: #fbfdfb;
  box-shadow: 0 30px 100px rgba(34,72,49,.24);
}
section[role="dialog"], section[role="dialog"] h2, section[role="dialog"] button {
  color: #17231d !important;
}
.metrics-intro { color: #607168; font-size: 11px; line-height: 1.6; margin: -4px 0 17px; }
.metrics-section-title { margin: 18px 0 8px; color: #2a3d33; font-size: 11px; font-weight: 650; }
.metrics-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 14px; }
.metrics-table { width: 100%; min-width: 690px; border-collapse: collapse; }
.metrics-table th, .metrics-table td { padding: 13px 14px; border-right: 1px solid var(--line-soft); border-bottom: 1px solid var(--line-soft); text-align: left; }
.metrics-table th:last-child, .metrics-table td:last-child { border-right: 0; }
.metrics-table tr:last-child td { border-bottom: 0; }
.metrics-table th { color: #65766d; background: rgba(41,105,66,.055); font-size: 8px; font-weight: 650; letter-spacing: .08em; text-transform: uppercase; }
.metrics-table td { color: #293b31; font-size: 11px; }
.metrics-table td:not(:first-child) { text-align: center; font-variant-numeric: tabular-nums; }
.metrics-table th:not(:first-child) { text-align: center; }
.metrics-table .best { color: #156c40; font-weight: 650; background: rgba(70,190,119,.075); }
.metrics-table .pending { color: #829188; font-size: 9px; }
.metrics-foot { margin-top: 12px; color: #6d7d74; font-size: 9.5px; line-height: 1.55; }

@media (max-width: 900px) {
  .block-container { padding-inline: 1rem !important; }
  [data-testid="stHorizontalBlock"] { flex-direction: column; }
  [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
  .method-card { min-height: 340px; }
  .topbar { margin-bottom: 2.2rem; }
}
@media (max-width: 560px) {
  .block-container { padding-top: .9rem !important; padding-bottom: 8.5rem !important; }
  .corpus-chip { display: none; }
  .hero { text-align: left; margin-bottom: 2rem; }
  .hero h1 { margin-left: 0; font-size: 38px; }
  .hero p { margin-left: 0; }
  .results-note { max-width: 230px; }
  .method-card { border-radius: 17px; }
}
</style>
"""


METHODS = (
    {
        "key": "semantic",
        "name": "Semantic Search",
        "stack": "Dense retrieval",
        "accent": "#7765da",
        "description": "Tìm theo ý nghĩa của câu hỏi bằng embedding; phù hợp khi cách diễn đạt giữa câu hỏi và tài liệu khác nhau.",
        "icon": '<svg viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="6.5" stroke="currentColor" stroke-width="1.7"/><path d="m16 16 4 4M8.5 11h5M11 8.5v5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    },
    {
        "key": "hybrid",
        "name": "Hybrid Search",
        "stack": "Dense + BM25 + RRF",
        "accent": "#168f8a",
        "description": "Kết hợp ngữ nghĩa với BM25 rồi hợp nhất thứ hạng bằng RRF để bắt tốt số hiệu văn bản, tên riêng và thuật ngữ chuyên ngành.",
        "icon": '<svg viewBox="0 0 24 24" fill="none"><path d="M4 7h7M4 12h11M4 17h16" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><circle cx="15" cy="7" r="2" fill="currentColor"/></svg>',
    },
    {
        "key": "reranker",
        "name": "Hybrid + Reranker",
        "stack": "Hybrid + Neural reranker",
        "accent": "#2a9d60",
        "description": "Chấm lại độ liên quan của các ứng viên Hybrid bằng neural reranker để đưa bằng chứng sát câu hỏi nhất lên đầu.",
        "icon": '<svg viewBox="0 0 24 24" fill="none"><path d="m5 16 4-4 3 3 7-8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M15 7h4v4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    },
)


def _safe_url(value: Any) -> str | None:
    """Return only links that are safe to expose as clickable sources."""
    if not isinstance(value, str):
        return None
    parsed = urlparse(value.strip())
    return value.strip() if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _answer_html(answer: str) -> str:
    paragraphs = [part.strip() for part in answer.split("\n\n") if part.strip()]
    if not paragraphs:
        return ""
    return "".join(f"<p>{escape(part).replace(chr(10), '<br>')}</p>" for part in paragraphs)


def _sources_html(chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return ""

    items: list[str] = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata") or {}
        title = str(metadata.get("title") or metadata.get("source") or "Nguồn không tên")
        legal_path = metadata.get("legal_path")
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")
        page_text = ""
        if page_start is not None:
            page_text = f"Trang {page_start}" if page_start == page_end or page_end is None else f"Trang {page_start}–{page_end}"
        meta_text = " · ".join(str(value) for value in (legal_path, page_text) if value)
        score = chunk.get("score")
        score_text = f" · score {float(score):.3f}" if isinstance(score, (int, float)) else ""
        url = _safe_url(metadata.get("url"))
        title_markup = escape(title)
        if url:
            title_markup = f'<a class="source-title" href="{escape(url, quote=True)}" target="_blank" rel="noopener">{title_markup}</a>'
        else:
            title_markup = f'<span class="source-title">{title_markup}</span>'
        items.append(
            f'<div class="source-item"><span class="source-rank">E{index}</span>{title_markup}'
            f'<div class="source-meta">{escape(meta_text)}{escape(score_text)}</div></div>'
        )

    return (
        '<div class="source-list"><details><summary>'
        f'{len(chunks)} nguồn được sử dụng</summary>{"".join(items)}</details></div>'
    )


def _empty_card(method: dict[str, str]) -> str:
    return f"""
    <section class="method-card" style="--accent:{method['accent']}">
      <div class="method-head">
        <div class="method-id"><div class="method-icon">{method['icon']}</div>
          <div><div class="method-name">{method['name']}</div><div class="method-stack">{method['stack']}</div></div>
        </div>
        <span class="status-pill">Sẵn sàng</span>
      </div>
      <div class="method-divider"></div>
      <div class="empty-state">
        <div><div class="answer-label">Cách hoạt động</div><p class="empty-copy">{method['description']}</p>
          <div class="empty-visual"><div class="empty-line"></div><div class="empty-line"></div><div class="empty-line"></div></div>
        </div>
        <div class="card-foot"><span>Chờ câu hỏi</span><span>Top-k {TOP_K}</span></div>
      </div>
    </section>
    """


def _result_card(method: dict[str, str], result: dict[str, Any]) -> str:
    error = result.get("error")
    chunks = result.get("sources") or []
    status_class = "error" if error else "live"
    status_text = "Cần kiểm tra" if error else "Hoàn tất"
    if error:
        body = f'<div class="answer-label">Pipeline chưa trả kết quả</div><p class="answer-error">{escape(str(error))}</p>'
    else:
        body = f'<div class="answer-label">Câu trả lời</div><div class="answer-text">{_answer_html(str(result.get("answer") or ""))}</div>'

    latency = result.get("latency_ms")
    latency_text = f"{float(latency):.0f} ms" if isinstance(latency, (int, float)) else "—"
    top_score = chunks[0].get("score") if chunks else None
    score_text = f"{float(top_score):.3f}" if isinstance(top_score, (int, float)) else "—"

    return f"""
    <section class="method-card" style="--accent:{method['accent']}">
      <div class="method-head">
        <div class="method-id"><div class="method-icon">{method['icon']}</div>
          <div><div class="method-name">{method['name']}</div><div class="method-stack">{method['stack']}</div></div>
        </div>
        <span class="status-pill {status_class}">{status_text}</span>
      </div>
      <div class="method-divider"></div>
      {body}
      <div class="stat-row">
        <div class="mini-stat"><strong>{latency_text}</strong><span>Latency</span></div>
        <div class="mini-stat"><strong>{len(chunks)}</strong><span>Chunks</span></div>
        <div class="mini-stat"><strong>{score_text}</strong><span>Top score</span></div>
      </div>
      {_sources_html(chunks)}
    </section>
    """


@st.cache_resource(show_spinner=False)
def _prepare_bm25_corpus() -> int:
    """Load the same chunks used by dense retrieval into the lexical retriever."""
    import src.task6_lexical_search as lexical
    from src.task4_chunking_indexing import chunk_documents, load_documents

    if not lexical.CORPUS:
        lexical.CORPUS = chunk_documents(load_documents())
    return len(lexical.CORPUS)


def _generate_answer(query: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    from src.citations import validate_citations
    from src.task10_generation import SYSTEM_PROMPT, call_llm, format_context, reorder_for_llm

    started = perf_counter()
    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "latency_ms": (perf_counter() - started) * 1000,
        }

    ordered = reorder_for_llm(chunks)
    answer = call_llm(
        SYSTEM_PROMPT,
        f"Evidence:\n{format_context(ordered)}\n\nQuestion: {query}",
    )
    validation = validate_citations(answer, ordered)
    if not validation["valid"]:
        answer = "Tôi không thể xác minh câu trả lời vì citation do mô hình tạo không hợp lệ."
    return {
        "answer": answer,
        "sources": chunks,
        "latency_ms": (perf_counter() - started) * 1000,
    }


def _pipeline_error(message: str) -> dict[str, Any]:
    return {"error": message, "answer": "", "sources": [], "latency_ms": None}


def run_comparison(query: str, top_k: int = TOP_K) -> dict[str, dict[str, Any]]:
    """Retrieve once, create three rankings, then generate answers concurrently."""
    from src.task4_chunking_indexing import CHROMA_DIR
    from src.task5_semantic_search import semantic_search
    from src.task6_lexical_search import lexical_search
    from src.task7_reranking import rerank_advanced, rerank_rrf

    if not CHROMA_DIR.exists():
        message = "Chưa có vector index. Hãy chạy `python -m src.task4_chunking_indexing` trước khi truy vấn."
        return {method["key"]: _pipeline_error(message) for method in METHODS}

    try:
        _prepare_bm25_corpus()
        candidate_k = max(top_k * 3, 12)
        dense = semantic_search(query, top_k=candidate_k)
        sparse = lexical_search(query, top_k=candidate_k)
        hybrid_candidates = rerank_rrf([dense, sparse], top_k=candidate_k)
        rankings = {
            "semantic": dense[:top_k],
            "hybrid": hybrid_candidates[:top_k],
            "reranker": rerank_advanced(query, hybrid_candidates, top_k=top_k),
        }
    except Exception as exc:  # Keep the UI usable when providers/index are unavailable.
        message = f"Không thể chạy retrieval: {exc}"
        return {method["key"]: _pipeline_error(message) for method in METHODS}

    outputs: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_generate_answer, query, chunks): key
            for key, chunks in rankings.items()
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                outputs[key] = future.result()
            except Exception as exc:
                outputs[key] = {
                    **_pipeline_error(f"Không thể sinh câu trả lời: {exc}"),
                    "sources": rankings[key],
                }
    return outputs


@st.dialog("Bảng so sánh metrics")
def show_metrics() -> None:
    local_metrics: dict[str, Any] = {}
    if BENCHMARK_RESULTS.exists():
        try:
            local_metrics = json.loads(BENCHMARK_RESULTS.read_text(encoding="utf-8")).get("metrics", {})
        except (OSError, json.JSONDecodeError):
            local_metrics = {}

    labels = (
        ("semantic", "Semantic"),
        ("hybrid_rrf", "Hybrid + RRF"),
        ("hybrid_reranker", "Hybrid + Reranker"),
    )
    local_rows = "".join(
        "<tr>"
        f"<td>{label}</td>"
        f"<td>{local_metrics.get(key, {}).get('source_hit_at_k', 0):.3f}</td>"
        f"<td>{local_metrics.get(key, {}).get('mrr', 0):.3f}</td>"
        f"<td>{local_metrics.get(key, {}).get('context_token_recall', 0):.3f}</td>"
        f"<td>{local_metrics.get(key, {}).get('avg_latency_ms', 0):.0f} ms</td>"
        "</tr>"
        for key, label in labels
    ) if local_metrics else '<tr><td colspan="5" class="pending">Chưa chạy local benchmark</td></tr>'

    st.markdown(
        f"""
        <p class="metrics-intro">Kết quả benchmark trên golden dataset 16 câu hỏi, cùng generator và top-k = 5. Dữ liệu lấy từ báo cáo đánh giá của project.</p>
        <div class="metrics-section-title">Local retrieval benchmark — kết quả chạy thật</div>
        <div class="metrics-wrap"><table class="metrics-table">
          <thead><tr><th>Strategy</th><th>Source hit@5</th><th>MRR</th><th>Context recall</th><th>Latency</th></tr></thead>
          <tbody>{local_rows}</tbody>
        </table></div>
        <div class="metrics-section-title">Ragas generation evaluation</div>
        <div class="metrics-wrap"><table class="metrics-table">
          <thead><tr><th>Metric</th><th>Semantic</th><th>Hybrid + RRF</th><th>Hybrid + Reranker</th></tr></thead>
          <tbody>
            <tr><td>Faithfulness</td><td>0.82</td><td>0.92</td><td class="pending">Chưa đo tách riêng</td></tr>
            <tr><td>Answer relevance</td><td>0.84</td><td>0.90</td><td class="pending">Chưa đo tách riêng</td></tr>
            <tr><td>Context recall</td><td>0.71</td><td>0.89</td><td class="pending">Chưa đo tách riêng</td></tr>
            <tr><td>Context precision</td><td>0.74</td><td>0.85</td><td class="pending">Chưa đo tách riêng</td></tr>
            <tr><td><strong>Average</strong></td><td><strong>0.78</strong></td><td><strong>0.89</strong></td><td class="best">0.92</td></tr>
            <tr><td>Retrieval latency</td><td>~280 ms</td><td>~340 ms</td><td>~465 ms</td></tr>
          </tbody>
        </table></div>
        <p class="metrics-foot">Hybrid + RRF tăng average +0.11 so với dense-only. Neural reranker tăng thêm +0.03 average trong bonus experiment; báo cáo chưa công bố điểm thành phần nên giao diện không suy diễn bốn metric riêng.</p>
        """,
        unsafe_allow_html=True,
    )


st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.markdown(
    """
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark"><svg viewBox="0 0 24 24" fill="none"><path d="M5 17.5 9 13l3 3 7-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M15 7h4v4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
        <div class="brand-copy"><strong>RAG Compare</strong><span>Retrieval lab</span></div>
      </div>
      <div class="corpus-chip"><i></i> Corpus pháp luật &amp; tin tức · 8 nguồn</div>
    </header>
    <section class="hero">
      <div class="eyebrow">Retrieval evaluation workspace</div>
      <h1>Một câu hỏi.<br>Ba cách truy xuất.</h1>
      <p>Đặt cùng một câu hỏi cho Semantic, Hybrid và Hybrid + Reranker để đối chiếu câu trả lời, nguồn dẫn và độ trễ trên cùng một màn hình.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

bar_left, bar_right = st.columns([4, 1], vertical_alignment="bottom")
with bar_left:
    st.markdown(
        '<div class="results-bar"><div><div class="results-title">Kết quả đối chiếu</div><div class="results-note">Cả ba pipeline dùng chung query, corpus, generator và top-k.</div></div></div>',
        unsafe_allow_html=True,
    )
with bar_right:
    if st.button("Xem bảng metrics", icon=":material/analytics:", use_container_width=False):
        show_metrics()

if "comparison" not in st.session_state:
    st.session_state.comparison = None
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

query = st.chat_input("Hỏi về Luật Phòng, chống ma túy, Etomidate hoặc Pod Chill…")
if query:
    cleaned_query = query.strip()
    if cleaned_query:
        st.session_state.last_query = cleaned_query
        with st.spinner("Đang chạy đồng thời 3 chiến lược retrieval…"):
            st.session_state.comparison = run_comparison(cleaned_query)

if st.session_state.last_query:
    st.markdown(
        f'<div class="query-strip"><span>Query</span>{escape(st.session_state.last_query)}</div>',
        unsafe_allow_html=True,
    )

columns = st.columns(3)
comparison = st.session_state.comparison
for column, method in zip(columns, METHODS):
    with column:
        card = _empty_card(method) if comparison is None else _result_card(method, comparison[method["key"]])
        st.markdown(card, unsafe_allow_html=True)
