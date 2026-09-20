# Individual contribution report

## Thông tin

- **Họ và tên:** Lương Quang Huy
- **Mã học viên:** (Điền MSSV của bạn)
- **Nhóm:** Team G36
- **Repository/branch:** `https://github.com/tuanfptu/K4-L3A-RAG-Pipeline-TeamG36` / branch `feature/chunking`

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Task 4: Structure-Aware Chunking & Indexing** | Thiết kế bộ chunking phân cấp bảo toàn ngữ cảnh điều khoản pháp luật (`Điều`, `Chương`, `Khoản`) kết hợp Recursive Splitter; Vector hóa batch qua Google GenAI API (`gemini-embedding-001`, 3072 dims) lưu trữ persistent ChromaDB; trích xuất URL citation từ metadata. | `src/task4_chunking_indexing.py`, `tests/test_contracts.py` (TestTask4Indexing) / commit `0bd313d` | Done |
| **Task 5: Dense Semantic Search** | Xây dựng semantic search query trực tiếp từ ChromaDB collection bằng Gemini embedding; chuẩn hóa khoảng cách cosine distance về similarity score `max(0.0, 1.0 - distance)`; gắn metadata `retrieval_method="dense"`. | `src/task5_semantic_search.py`, `tests/test_contracts.py` (TestTask5SemanticSearch) | Done |
| **Task 6: Lexical Search (BM25Plus)** | Xây dựng bộ tìm kiếm từ khóa chính xác BM25Plus (bổ sung lower-bounding parameter $\delta=1.0$ để tránh penalize các văn bản ngắn/sparse IDF); tiền xử lý tokenizer regex tiếng Việt; cơ chế lazy indexing & index caching tránh re-index tốn tài nguyên. | `src/task6_lexical_search.py`, `tests/test_contracts.py` (TestTask6LexicalSearch) | Done |
| **Task 7: Reranking & Hybrid Fusion (RRF & Neural Reranker)** | 1) Hiện thực Reciprocal Rank Fusion (`rerank_rrf` với hằng số $k=60$) kết hợp dense rank & sparse rank độc lập scale, zero hyperparameter-tuning.<br>2) Hiện thực Cross-Attention Neural Reranker (`rerank_advanced` với Gemini 3.5 Flash / Jina Reranker) đạt **+3 Bonus điểm**, chấm điểm relevance 0-1 và re-rank lại top retrieved docs. | `src/task7_reranking.py`, `tests/test_contracts.py` (TestTask7Reranking) | Done (+3 Bonus) |
| **Task 8: Vectorless Fallback** | Xây dựng cơ chế fallback an toàn (`pageindex_retrieve`) khi không có `PAGEINDEX_API_KEY` hoặc lỗi mạng; graceful degradation trả về danh sách rỗng thay vì làm crash toàn bộ RAG pipeline. | `src/task8_pageindex_vectorless.py` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng Structure-aware Chunking theo cấu trúc phân cấp pháp luật (Điều, Khoản, Mục) thay vì Fixed-size character/token chunking thông thường.  
   **Lý do/evidence:** Văn bản quy phạm pháp luật và tài liệu quy chế có tính toàn vẹn ngữ cảnh rất cao ở cấp "Điều/Khoản". Nếu cắt vụn theo fixed-character (ví dụ 500 ký tự), một điều luật sẽ bị cắt xén làm 2-3 phần, làm mất liên kết giữa tiêu đề điều luật và chế tài cụ thể. Thử nghiệm trên 1,360 tài liệu thực tế của đề tài sinh ra 1,822 chunks hoàn chỉnh, mỗi chunk đại diện trọn vẹn một điều khoản kèm đầy đủ URL và metadata nguồn.  
   **Trade-off:** Độ dài các chunk không đồng đều tuyệt đối (một số điều ngắn ~150 ký tự, một số điều dài ~1500 ký tự), đòi hỏi phải kết hợp RecursiveCharacterTextSplitter để sub-chunk các điều quá dài nhằm tránh vượt token limit của embedding model.

2. **Quyết định:** Áp dụng Reciprocal Rank Fusion (RRF, $k=60$) cho Config B thay vì Linear Weighted Score Fusion ($\alpha \cdot S_{dense} + (1-\alpha) \cdot S_{bm25}$).  
   **Lý do/evidence:** Điểm cosine similarity của dense vector nằm trong khoảng $[0, 1]$, trong khi điểm BM25 là log-odds uncalibrated không bị chặn trên. Việc chuẩn hóa Min-Max cho BM25 phụ thuộc chặt chẽ vào phân phối điểm của từng query cụ thể và dễ bị mất ổn định trên out-of-distribution queries. RRF là rank-based: $RRF(d) = \sum \frac{1}{k + r(d)}$, loại bỏ hoàn toàn rủi ro scale mismatch và không cần tune siêu tham số $\alpha$, tránh data leakage trên tập golden.  
   **Trade-off:** RRF không tận dụng được biên độ tự tin tuyệt đối (confidence margin) của mô hình retrieval khi một tài liệu có score vượt trội hoàn toàn; tuy nhiên đổi lại độ bền vững cực cao trên toàn bộ các dạng câu hỏi (cả từ khóa chuyên ngành lẫn ngữ nghĩa ẩn).

---

## Kiểm thử và kết quả

- **Test hoặc query tôi đã dùng:**
  - Bộ unit test hợp đồng: `pytest tests/test_contracts.py -k "Task4 or Task5 or Task6 or Task7"` đạt 4/4 passed (100%).
  - Chạy thực nghiệm trên dữ liệu thật của nhóm (1,360 tài liệu từ `data/standardized/`, tạo 1,822 chunks và index thành công vào ChromaDB persistent directory `data/chroma_db`).
  - Truy vấn kiểm thử thực tế đa dạng: Query ngữ nghĩa ("quy trình xử lý vi phạm hợp đồng") và Query từ khóa mã hiệu ("Nghị định 100").
- **Kết quả trước/sau nếu có:**
  - *Trước:* Chưa có vector store và lexical index; truy vấn đơn lẻ chỉ bắt được từ khóa hoặc chỉ bắt được ngữ nghĩa mờ nhạt; BM25Okapi mặc định dễ sinh IDF âm/0 khi từ khóa xuất hiện ở > 50% văn bản ngắn.
  - *Sau:* Hệ thống hybrid search kết hợp dense (Gemini 3072 dims) + sparse (BM25Plus) trả về top-5 tài liệu chính xác vượt trội; RRF kết hợp nhịp nhàng cả 2 nguồn; Neural reranker (Gemini 3.5 Flash) lọc và chấm điểm relevance trực tiếp cho từng cặp query-context.
- **Lỗi đã phát hiện và cách xử lý:**
  - *Lỗi 1:* Thiếu API key bên thứ 3 (PageIndex) ở Task 8 gây crash pipeline -> Xử lý bằng try/except và graceful fallback trả về list rỗng kèm log cảnh báo.
  - *Lỗi 2:* ChromaDB metadata không nhận list/dict phức tạp -> Serialize thành string và chuẩn hóa type về primitives trước khi add vào collection.

---

## Điều còn hạn chế

- **Một hạn chế cụ thể của phần tôi làm:** Tốc độ gọi API embedding online (Gemini cloud embedding) và Neural Reranker phụ thuộc vào latency mạng và quota rate limit của Google AI Studio (15 RPM ở tier miễn phí).
- **Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:** Bổ sung cơ chế local cache embedding (SQLite/diskcache) cho các query lặp lại, hoặc benchmark thêm mô hình local dense embedding (`bge-m3` hoặc `phobert`) chạy offline hoàn toàn để tối ưu latency (<50ms) và hoàn toàn độc lập với internet.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 20/09/2026
- **Tên thành viên:** Lương Quang Huy

