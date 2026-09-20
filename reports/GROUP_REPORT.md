# Báo cáo nhóm G36 — RAG pháp luật về Etomidate và Pod Chill

## 1. Thông tin dự án

- Repository: [tuanfptu/K4-L3A-RAG-Pipeline-TeamG36](https://github.com/tuanfptu/K4-L3A-RAG-Pipeline-TeamG36)
- Chủ đề: Tra cứu pháp luật và thông tin công khai về Etomidate, Pod Chill và ma túy mới tại Việt Nam
- Thành viên: Hà Mạnh Tuân, Lương Quang Huy, Lương Khánh Toàn, Đặng Quốc Cường
- Stack chính: Python, Streamlit, Gemini, PyMuPDF, Tesseract, ChromaDB, BM25Plus và RRF

## 2. Mục tiêu và phạm vi

Nhóm xây dựng hệ thống RAG có thể trả lời câu hỏi từ nguồn pháp luật và bài viết công khai, đồng thời truy vết mỗi bằng chứng về đúng nguồn. Với văn bản pháp luật, citation giữ số hiệu văn bản, Điều/Khoản/Điểm, trang PDF và URL chính thức. Với bài viết, citation giữ publisher, tiêu đề, ngày đăng và URL.

Hệ thống so sánh ba chiến lược trên cùng query, corpus, generator và `top_k = 5`:

1. Semantic Search.
2. Hybrid Search: Dense + BM25Plus + RRF.
3. Hybrid + Neural Reranker.

## 3. Phân công và bằng chứng đóng góp

| Thành viên | Phần việc chính | Bằng chứng |
|---|---|---|
| Hà Mạnh Tuân — 2A202602982 | Source registry; PDF page extraction; OCR; Gemini structuring; article normalization; provenance; legal citation schema | `src/legal_pdf_pipeline.py`, `src/article_pipeline.py`, `src/data_pipeline.py`, `src/citations.py`, commit `f8a3e71` |
| Lương Quang Huy | Structure-aware chunking; Gemini/local embeddings; ChromaDB; Dense Search; BM25Plus; RRF và advanced reranker | `src/task4_chunking_indexing.py` đến `src/task8_pageindex_vectorless.py`, commits `964c902`, `47a8c41` |
| Lương Khánh Toàn — 2A202602836 | Retrieval orchestration; dense-score fallback; evidence context; generation; citation validation; tích hợp chatbot | `src/task9_retrieval_pipeline.py`, `src/task10_generation.py`, commit `1869ebc` |
| Đặng Quốc Cường | Golden dataset; benchmark retrieval; A/B report; UI so sánh ba pipeline; kiểm thử acceptance | `src/evaluate_retrieval.py`, `group_project/evaluation/`, `app.py`, commit `5c639d2` |

Chi tiết ownership nằm trong các file cá nhân tại `reports/`.

## 4. Dữ liệu và ingestion

Corpus canonical gồm 8 nguồn:

- 3 PDF pháp lý chính thức: Luật 73/2021/QH14, Nghị định 28/2026/NĐ-CP và Nghị định 163/2026/NĐ-CP.
- 5 bài viết công khai từ Bộ Công an và VTV.

Kết quả xử lý PDF:

| Chỉ số | Kết quả |
|---|---:|
| Tổng số trang | 171 |
| Native-text pages | 33 |
| OCR pages | 138 |
| Trang extraction rỗng | 0 |
| Legal records | 1.355 |
| Record ID duy nhất | 1.355 |
| Records có Điều | 801 |
| Records có Khoản | 789 |
| Records có Điểm | 601 |

PDF được xử lý theo từng trang. Source of truth là PDF gốc; raw OCR/native text được giữ tại `data/extracted/`. Gemini chỉ nhận diện cấu trúc và metadata, không được dùng làm nguồn sự thật. Stable ID, file SHA256, extraction method, OCR confidence, page range và URL nguồn được giữ đến record cuối.

## 5. Chunking, embedding và indexing

- Legal records được ưu tiên chia theo đơn vị cấu trúc; record dài mới được recursive subchunk.
- Article được recursive chunk với `chunk_size = 500`, overlap 50.
- Metadata nguồn và citation được sao chép vào mọi subchunk.
- ChromaDB dùng cosine distance và upsert theo stable ID để index lại không sinh bản ghi trùng.
- Provider mặc định theo `.env`: Gemini `gemini-embedding-001`; benchmark retrieval đã lưu dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` để chạy tái lập cục bộ.

## 6. Retrieval và generation

Dense Search đổi cosine distance thành similarity. BM25Plus dùng tokenizer tiếng Việt đơn giản và cache corpus/index. RRF hợp nhất thứ hạng đúng một lần theo công thức:

```text
RRF(d) = Σ 1 / (60 + rank(d))
```

Fallback so sánh `SCORE_THRESHOLD` với cosine score gốc của Dense, không dùng RRF score. Generation nhận context gắn ID `[E1]`, `[E2]` và không được tự tạo URL. Citation validator từ chối ID không nằm trong evidence đã retrieve.

UI demo chạy cùng một câu hỏi qua ba ranking strategy, hiển thị answer, số chunk, top score, latency và nguồn dẫn. Các lần gọi Gemini generation được thực hiện tuần tự để tránh burst rate limit.

## 7. Evaluation

Golden dataset có 16 câu hỏi grounded, bao phủ cả ba văn bản pháp luật và năm bài viết. Benchmark retrieval chạy thật cho kết quả:

| Strategy | Source hit@5 | MRR | Context token recall | Latency trung bình |
|---|---:|---:|---:|---:|
| Semantic | 0,9375 | 0,8875 | 0,6927 | 1.714 ms |
| Hybrid + RRF | 1,0000 | 0,9583 | 0,7166 | 1.743 ms |
| Hybrid + Reranker | 1,0000 | 0,9583 | 0,7166 | 2.753 ms |

Hybrid + RRF tăng MRR thêm 0,0708 và đạt source hit@5 tuyệt đối trên tập 16 câu. Neural reranker chưa cải thiện retrieval metrics trên tập hiện tại nhưng tăng latency khoảng một giây; vì vậy Hybrid + RRF là cấu hình cân bằng tốt nhất cho demo.

Bốn điểm Ragas trong `reports/RESULT.md` là kết quả báo cáo/ước lượng của nhóm, chưa phải output trực tiếp từ một lần chạy Ragas LLM-as-judge. Nhóm giữ ghi chú này để không trình bày số ước lượng như phép đo thực nghiệm.

## 8. Kiểm thử và khả năng tái lập

```bash
python -m pip install -e ".[dev]"
python -m src.task4_chunking_indexing
pytest -q
streamlit run app.py
```

Kết quả hiện tại: `24 passed`. Pipeline ingestion chạy lại dùng cache theo input hash/model; raw source không bị ghi đè. `.env` bị ignore và không có API key trong repository.

## 9. Kịch bản demo

1. Mở app và kiểm tra trạng thái corpus/vector index ở sidebar.
2. Chạy câu in-domain: “Nghị định 28/2026/NĐ-CP quy định trách nhiệm quản lý ra sao?”.
3. So sánh nguồn, score và latency giữa Semantic, Hybrid và Hybrid + Reranker.
4. Mở URL citation và đối chiếu Điều/Khoản/trang PDF.
5. Chạy câu out-of-domain: “Công thức làm bánh mì là gì?” để kiểm tra safe refusal/fallback.
6. Mở bảng metrics để trình bày kết quả A/B.

## 10. Hạn chế và hướng phát triển

- OCR bảng hóa chất của Nghị định 28 có chất lượng thấp hơn trang văn bản; mã CAS và công thức hóa học cần đối chiếu PDF gốc.
- Vector index không commit vào Git; máy demo phải chạy Task 4 sau khi cấu hình embedding provider.
- Reranker dùng API làm tăng latency và có thể bị quota; cần cache query/rerank hoặc benchmark reranker local.
- Cần chạy Ragas trực tiếp trên 16 câu để thay thế hoàn toàn bốn điểm ước lượng bằng measurement có raw output.
- Có thể bổ sung conversation memory và source highlighting theo từng claim để đạt bonus UI/memory.

## 11. Kết luận

Nhóm đã hoàn thiện pipeline từ raw source đến citation-ready evidence, hybrid retrieval, generation có kiểm chứng citation, golden dataset, benchmark A/B và giao diện demo. Kết quả retrieval thực nghiệm cho thấy Hybrid + RRF là lựa chọn phù hợp nhất cho corpus pháp luật có nhiều số hiệu, tên riêng và cấu trúc Điều/Khoản/Điểm.
