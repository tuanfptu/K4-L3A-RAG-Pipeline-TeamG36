# Day 8 — RAG Pipeline

## Mục tiêu

Mỗi nhóm xây dựng một chatbot RAG trả lời câu hỏi từ bộ tài liệu do nhóm thu thập. Sản phẩm phải có hybrid retrieval, citation, giao diện chat và báo cáo đánh giá.

Nhóm tự chọn bài toán và thu thập dữ liệu phù hợp; repo không cung cấp dữ liệu mẫu.

## Sản phẩm phải nộp

- Repository nhóm chạy được.
- Tối thiểu 3 tài liệu chính sách và 5 bài viết/page do nhóm tự thu thập.
- Pipeline: convert → chunk → index → dense + BM25 → RRF → fallback → generation có citation.
- Chatbot Streamlit hiển thị câu trả lời và nguồn đã dùng.
- Golden dataset tối thiểu 15 câu; đánh giá 4 metric và so sánh A/B.
- `group_project/evaluation/RESULT.md`.
- Mỗi thành viên nộp báo cáo cá nhân theo template trong `group_project/ịndividual/INDIVIDUAL_REPORT.md`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
python -m playwright install chromium
cp .env.example .env
```

Điền API key cần dùng trong `.env`; không commit file này.

```bash
# 1. Thu thập và chuẩn hoá
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown

# 2. Index và kiểm tra contract
python -m src.task4_chunking_indexing
pytest -q

# 3. Chạy sản phẩm
streamlit run app.py
```

Giao diện demo hiển thị trạng thái corpus/vector index trong sidebar, cung cấp
câu hỏi in-domain và out-of-domain, đồng thời so sánh Semantic, Hybrid + RRF và
Hybrid + Reranker trên cùng một màn hình. Trước lần demo đầu tiên, tạo index rồi
khởi động app:

```bash
python -m src.task4_chunking_indexing
streamlit run app.py
```

## Lộ trình 3 giờ

| Mốc                  | Thời gian | Kết quả cần có                           |
| -------------------- | --------: | ---------------------------------------- |
| 0. Setup             |   10 phút | Môi trường và `.env` sẵn sàng            |
| 1. Data              |   25 phút | ≥3 legal, ≥5 news, Markdown đã chuẩn hoá |
| 2. Index & search    |   30 phút | ChromaDB, dense search và BM25 chạy được |
| 3. Fusion & fallback |   25 phút | RRF và fallback tuân thủ contract        |
| 4. Generation & UI   |   30 phút | Chatbot trả lời có citation              |
| 5. Evaluation        |   30 phút | 15+ Q&A, 4 metric, A/B comparison        |
| 6. Demo & handoff    |   30 phút | Test, report, demo và push repository    |

## Lưu ý quy tắc để có code quality tốt:

- Dense và BM25 nên cùng trả về `SearchResult` theo một schema.
- RRF chỉ nên dùng để gộp thứ hạng và chỉ chạy một lần.
- Fallback dùng cosine score gốc của dense retrieval.
- Threshold phải được hiệu chỉnh trên query in domain và out of domain, không có một con số đúng cho mọi corpus.

## Tài liệu

- [Module contracts](docs/MODULE_CONTRACTS.md): schema, interface và invariant mà code/test nên tuân theo.
- [Step-by-step guide](docs/STEP_BY_STEP.md): thứ tự triển khai và tiêu chí hoàn thành từng bước.
- [Grading rubric](docs/GRADING_RUBRIC.md): Rubric thang điểm.
- [Individual report](group_project/ịndividual/INDIVIDUAL_REPORT.md): template báo cáo cá nhân.
- [Suggested topics](docs/SUGGESTED_TOPICS.md): danh sách chủ đề tham khảo, không bắt buộc.
- [Group report](reports/GROUP_REPORT.md): kiến trúc, phân công, số liệu corpus, benchmark và kịch bản demo.

## Kiểm tra

```bash
# Contract tests
pytest tests/test_contracts.py -q

# Acceptance tests
pytest tests/test_acceptance.py -q

# Toàn bộ
pytest -q
```

## Etomidate Citation-Ready Corpus Pipeline

Corpus gồm 3 PDF pháp lý chính thức và 5 bài báo về Etomidate/Pod Chill. Metadata
canonical của cả 8 nguồn nằm tại `data/sources.json`. Luồng PDF là: PDF bất biến →
native text theo trang → OCR Tesseract `vie+eng` khi text kém → raw page JSON →
Gemini structured output → validation → JSONL/Markdown. Bài báo giữ raw Crawl4AI,
SHA256, URL/ngày đăng và được chuẩn hóa riêng. Gemini chỉ cấu trúc, không phải nguồn sự thật.

```bash
pip install -e ".[dev]"
# OCR là tùy chọn; cần cài Tesseract và language pack vie trên hệ điều hành:
pip install -e ".[ocr]"
cp .env.example .env

# Smoke test offline 3 trang (không gọi Gemini, không OCR):
python -m src.data_pipeline --pdf --source-id nd28_2026 --max-pages 3 --skip-ocr --skip-gemini

# Chạy PDF bằng Gemini/OCR hoặc toàn corpus:
python -m src.data_pipeline --pdf --source-id nd28_2026 --max-pages 3
python -m src.data_pipeline --all
```

Outputs: raw pages ở `data/extracted/legal/<source_id>/`, canonical legal JSONL ở
`data/structured/legal/`, article JSON ở `data/structured/news/`, và compatibility
outputs ở `data/standardized/`. JSONL chứa một legal element mỗi dòng, stable ID,
SHA256 file, page range và `legal_path`. Task 4 ưu tiên một clause/point thành một
logical chunk và chỉ subchunk record dài.

Citation được render từ metadata đã retrieve, ví dụ
`Nghị định 28/2026/NĐ-CP — Điều 4, Khoản 2 — Trang 13`; generation chỉ được dùng
evidence ID `[E1]`, `[E2]`, không tự sinh URL. Khi OCR lỗi, xem `data/errors.jsonl`
và các `page_NNN.json`; có thể dùng `--skip-ocr` để kiểm tra native extraction.
Cache/outputs dùng stable hash và ghi đè cùng path nên chạy lại không tạo duplicate;
`--force` dành cho lần cần tái xử lý.
