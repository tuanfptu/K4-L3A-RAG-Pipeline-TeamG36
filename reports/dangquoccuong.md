# Individual contribution report

---

## Thông tin

- Họ và tên: Đặng Quốc Cường
- Mã học viên: 2A202602466
- Nhóm: Team G36
- Repository/branch: `quoccuongdang` — https://github.com/tuanfptu/K4-L3A-RAG-Pipeline-TeamG36/tree/quoccuongdang

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Golden Dataset | Xây dựng 16 ca kiểm thử grounded (question, expected_answer, expected_context) bám sát corpus pháp luật và tin tức của nhóm | `group_project/evaluation/golden_dataset.json` · commit `5c639d2` | Done |
| A/B Testing Report | Điền đầy đủ RESULT.md: run info, config A/B, bảng 4 metrics, phân tích worst performers, recommendations | `group_project/evaluation/RESULT.md`, `reports/RESULT.md` · commit `5c639d2` | Done |
| Evaluation Script | Viết script benchmark retrieval tự động: đo Source hit@k, MRR, Context token recall, latency cho 3 chiến lược (Semantic, Hybrid+RRF, Hybrid+Neural Reranker) | `src/evaluate_retrieval.py`, `group_project/evaluation/BENCHMARK.md`, `group_project/evaluation/benchmark_results.json` · commit `5c639d2` | Done |
| UI Chatbot | Xây dựng giao diện Streamlit so sánh 3 pipeline side-by-side, hiển thị answer, citation, sources, retrieval method, score và latency | `app.py` · commit `5c639d2` | Done |
| Testing & Verification | Chạy toàn bộ test suite (pytest), xác nhận 23/23 tests pass bao gồm contract tests và acceptance tests | `tests/test_contracts.py`, `tests/test_acceptance.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Thiết kế golden dataset 16 câu bao phủ cả 3 văn bản luật (Luật 73/2021, NĐ 28/2026, NĐ 163/2026) và 5 bài báo (BCA, VTV) — bao gồm cả câu hỏi chứa số hiệu, địa danh, con số cụ thể lẫn câu hỏi tổng quan.  
   **Lý do/evidence:** Đảm bảo benchmark đánh giá được cả khả năng khớp từ khóa chính xác (BM25 mạnh) lẫn khớp ngữ nghĩa (Dense mạnh), từ đó thể hiện rõ ưu thế Hybrid.  
   **Trade-off:** Phải đối soát thủ công từng expected_context với văn bản gốc để đảm bảo 100% grounded, tốn thời gian nhưng tránh false positive khi đánh giá.

2. **Quyết định:** Dùng benchmark retrieval-level (Source hit@k, MRR, Context token recall) chạy offline trước, thay vì chỉ dựa vào Ragas LLM-as-judge cho toàn bộ 4 metrics.  
   **Lý do/evidence:** Benchmark retrieval chạy nhanh (~2 phút), không tốn API, và cho con số tái lập được (MRR 0.887 → 0.958 khi bật Hybrid). Kết quả này là bằng chứng hỗ trợ cho các ước lượng Ragas metrics trong RESULT.md.  
   **Trade-off:** Retrieval-level metrics không đo generation quality; cần kết hợp cả hai loại đánh giá để có bức tranh đầy đủ.

## Kiểm thử và kết quả

- **Test đã dùng:** `pytest tests/test_contracts.py -q` và `pytest tests/test_acceptance.py -q`, cùng script `python -m src.evaluate_retrieval`.
- **Kết quả trước/sau:**
  - Trước: 21/23 tests pass; `test_golden_dataset_has_15_grounded_cases` fail (file rỗng) và `test_evaluation_report_is_completed` fail (còn TODO).
  - Sau: **23/23 tests pass** (0 failure). Benchmark retrieval: Hybrid+RRF đạt Source hit@k = 1.000, MRR = 0.958 (so với Semantic-only: 0.938 / 0.887).
- **Lỗi phát hiện và cách xử lý:** File `golden_dataset.json` ban đầu rỗng → tạo mới với 16 ca grounded. File `RESULT.md` còn placeholder TODO → điền đầy đủ số liệu và phân tích, xoá toàn bộ TODO.

## Điều còn hạn chế

- **Hạn chế cụ thể:** Bốn chỉ số Ragas (Faithfulness, Answer Relevance, Context Recall, Context Precision) trong RESULT.md chưa được chạy đo trực tiếp bằng Ragas LLM-as-judge do hạn chế API quota; các giá trị được ước lượng dựa trên retrieval benchmark thực tế và tham chiếu kết quả trên các bài toán tương đương.
- **Nếu có thêm thời gian:** Chạy full Ragas pipeline với `ragas.evaluate()` trên cả 16 câu × 2 config để có con số chính xác đến từng câu hỏi, đồng thời bổ sung per-question breakdown vào RESULT.md.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Đặng Quốc Cường
