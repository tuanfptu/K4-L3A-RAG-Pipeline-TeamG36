# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-20 |
| Framework and version | Ragas 0.4.3; Pytest 8.x |
| Evaluator model | gemini-3.6-flash |
| Generator model | gemini-3.6-flash |
| Embedding model | BAAI/bge-m3 |
| Corpus version/commit | `f8a3e71` — citation-ready legal and news ingestion pipeline |
| Golden dataset size | 16 grounded questions |
| `top_k` | 5 |
| Fallback threshold and calibration | `score_threshold = 0.65`; in-domain dense scores 0.72–0.91, out-of-domain 0.35–0.58 |

## Configurations

- **Config A — dense-only:** truy vấn ChromaDB bằng embedding BAAI/bge-m3 và cosine similarity; không kết hợp BM25 hoặc reranker.
- **Config B — hybrid + RRF:** chạy Dense Search và BM25Plus trên cùng corpus, sau đó hợp nhất thứ hạng một lần bằng Reciprocal Rank Fusion với `k = 60`.

Hai cấu hình dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; biến độc lập duy nhất là chiến lược retrieval.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
| Faithfulness | 0.82 | 0.92 | +0.10 |
| Answer relevance | 0.84 | 0.90 | +0.06 |
| Context recall | 0.71 | 0.89 | +0.18 |
| Context precision | 0.74 | 0.85 | +0.11 |
| **Average** | **0.78** | **0.89** | **+0.11** |

## A/B comparison

- **Cấu hình tốt hơn:** Config B (Hybrid + RRF) tốt hơn Config A trên cả bốn metric; mức tăng lớn nhất là Context Recall (+0.18).
- **Evidence:** corpus pháp luật có nhiều định danh chính xác như “Nghị định 28/2026/NĐ-CP”, “Luật số 73/2021/QH14”, tên cơ quan, địa danh và hoạt chất. Dense-only thường gom các đoạn có ý nghĩa chung nhưng bỏ lỡ đúng điều/khoản; BM25 bắt được định danh, còn RRF ưu tiên các chunk xuất hiện cao ở cả hai danh sách.
- **Trade-off về latency/cost:** latency retrieval trung bình tăng từ khoảng 280 ms lên 340 ms mỗi query. Chi phí API generation không đổi vì hai cấu hình đều đưa đúng năm chunk vào cùng generator; BM25Plus và RRF chạy cục bộ.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Thời hạn quản lý người sử dụng trái phép chất ma túy theo Luật số 73/2021/QH14 là bao lâu? | Config A | 0.70 | 0.75 | 0.50 | 0.45 | retrieval | Dense-only trả về nhiều đoạn chứa từ chung “quản lý” và “ma túy”, làm Điều 23 Khoản 2 rơi khỏi top 5. |
| 2 | Nghị định 163/2026/NĐ-CP quy định chi tiết những nội dung chính nào của Luật Phòng, chống ma túy? | Config A | 0.75 | 0.80 | 0.60 | 0.60 | retrieval | Văn bản dài 100 trang; các đoạn giới thiệu tổng quan bị phân tán nên embedding thiếu tập trung. |
| 3 | Các hành vi nào bị nghiêm cấm theo Điều 5 Luật Phòng, chống ma túy số 73/2021/QH14? | Config B | 0.85 | 0.85 | 0.75 | 0.80 | generation | Điều 5 có danh sách dài; generator có xu hướng nhóm và tóm tắt thay vì giữ đủ từng hành vi. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Dùng Parent-Document hoặc Hierarchical Chunking cho văn bản pháp luật dài | Ca lỗi #2 cho thấy chunk nhỏ làm mất cấu trúc tổng thể của Nghị định 163/2026 | Tăng Context Recall của câu hỏi tổng quan từ 0.60 lên trên 0.90 | Chạy lại ca #2 với parent chunk và so sánh top-5 context |
| 2 | Thêm chỉ dẫn giữ nguyên danh sách điều luật trong prompt generation | Ca lỗi #3 bị thiếu ý do mô hình tóm lược | Nâng độ đầy đủ và Faithfulness lên trên 0.95 | Đánh giá lại nhóm câu hỏi liệt kê ở Điều 5 |
| 3 | Chuẩn hóa/expand từ viết tắt như NĐ, QH, BCA trước retrieval | BM25 phụ thuộc token bề mặt | Tăng Context Precision 3–5% cho truy vấn tự nhiên hoặc không dấu | Tạo các biến thể query viết tắt và chạy A/B |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| --- | --- | ---: | ---: | --- |
| BGE/Jina multilingual neural reranker sau Hybrid + RRF | Config B | +0.03 Average | khoảng +125 ms; không tăng chi phí khi self-host | Reranker cải thiện thứ hạng ứng viên khó, nhưng Hybrid + RRF vẫn là cấu hình cân bằng tốt nhất cho latency tương tác. |

## Reproducibility notes

- Golden cases nằm tại `group_project/evaluation/golden_dataset.json` và chỉ sử dụng nội dung có trong corpus.
- Retrieval fallback so sánh threshold với cosine score gốc của Dense, không dùng RRF score vì hai thang đo khác nhau.
- UI so sánh thêm cấu hình Hybrid + Neural Reranker; chỉ Average của bonus experiment được công bố, vì vậy không suy diễn điểm thành phần còn thiếu.
