# Individual contribution report

## Thông tin

- Họ và tên: Hà Mạnh Tuân
- Mã học viên: 2A202602982
- Nhóm: G36
- Repository/branch: [tuanfptu/K4-L3A-RAG-Pipeline-TeamG36](https://github.com/tuanfptu/K4-L3A-RAG-Pipeline-TeamG36) — `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Source registry và provenance | Chuẩn hóa registry cho 3 PDF pháp lý và 5 bài viết; giữ URL chính thức, publisher, trust level, local filename và source ID ổn định. | `data/sources.json`, commit [`f8a3e71`](https://github.com/tuanfptu/K4-L3A-RAG-Pipeline-TeamG36/commit/f8a3e7144f1f61f101649f18fdd08e1ae0d82a41) | Done |
| Legal PDF ingestion | Xây dựng pipeline extraction theo từng trang, phân biệt native/scanned PDF, OCR tiếng Việt, SHA256, raw page records và xử lý lỗi độc lập theo trang. | `src/legal_pdf_pipeline.py`, `data/extracted/legal/` | Done |
| Gemini structuring | Dùng Gemini structured output và Pydantic để nhận diện metadata văn bản, Chương/Mục/Điều/Khoản/Điểm; bổ sung pacing, retry/backoff và cache để tránh rate limit. | `src/legal_pdf_pipeline.py`, `.env.example` | Done |
| Article ingestion | Chuẩn hóa 5 bài Etomidate/Pod Chill, giữ publisher, ngày đăng, URL, content hash, topics/entities và exact-hash deduplication. | `src/article_pipeline.py`, `data/structured/news/` | Done |
| Citation-ready outputs | Sinh legal JSONL/Markdown với stable ID, page range, legal path, extraction method, OCR confidence, model và provenance; triển khai formatter/validator citation. | `src/citations.py`, `data/structured/legal/`, `data/standardized/` | Done |
| Task 4/10 compatibility | Mở rộng loader và structure-aware chunking cho legal/news; format evidence `[E1]`; chặn evidence ID giả sau generation. | `src/task4_chunking_indexing.py`, `src/task10_generation.py` | Done |
| CLI và kiểm thử | Tạo CLI thống nhất, test stable ID/legal path/citation, chạy full corpus và kiểm tra idempotence. | `src/data_pipeline.py`, `tests/test_citation_ready_pipeline.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Xử lý PDF theo từng trang và chỉ OCR những trang không đạt heuristic native text.  
   **Lý do/evidence:** Corpus có 171 trang; 33 trang đọc native tốt và 138 trang scan cần OCR. Thiết kế này giữ chính xác page provenance và tránh OCR không cần thiết.  
   **Trade-off:** Pipeline phức tạp và chạy lâu hơn convert toàn PDF thành một chuỗi, nhưng citation có thể truy ngược đúng trang và raw extraction.

2. **Quyết định:** Dùng stable deterministic ID, structured output/Pydantic và Gemini chạy tuần tự có pacing 4,2 giây.  
   **Lý do/evidence:** Full run sinh 1.355 legal records với 1.355 ID duy nhất, không gặp HTTP 429; lần chạy lại trả cache hit cho cả 3 PDF và 5 articles.  
   **Trade-off:** Throughput thấp hơn xử lý song song, đổi lại hạn chế rate limit, tránh duplicate và giúp kết quả có thể tái lập.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `python -m src.data_pipeline --pdf --source-id nd28_2026 --max-pages 3`
  - `python -m src.data_pipeline --all --force`
  - `pytest tests/test_contracts.py tests/test_citation_ready_pipeline.py -q`
- Kết quả:
  - Xử lý đủ 171/171 trang: 33 native, 138 OCR, không có trang rỗng.
  - Sinh 1.355 legal records và 5 article records, không có duplicate ID/content hash.
  - Task 4 load 1.360 documents và tạo 1.697 chunk ID duy nhất.
  - 18/18 contract và ingestion tests pass; toàn suite đạt 21 pass, còn 2 acceptance tests ngoài phạm vi ingestion thất bại vì golden dataset rỗng và evaluation report còn `TODO`.
- Lỗi đã phát hiện và cách xử lý:
  - Phát hiện Nghị định 28/163 gần như toàn bộ là scanned PDF; cài Tesseract 5.4 và language pack `vie+eng`.
  - Sửa cấu hình `tessdata` trên Windows sau khi đường dẫn có dấu quote làm OCR không load được language pack.
  - Chuẩn hóa output Gemini dạng `Điều 21` về số `21` trước validation mà không sửa nội dung pháp luật.

## Điều còn hạn chế

- Các trang bảng hóa chất trong Nghị định 28 có OCR thấp hơn văn bản thường; tên hóa học, ký hiệu và mã CAS cần được đối chiếu PDF gốc khi độ chính xác có tính quyết định.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: bổ sung table-aware OCR/layout extraction và bộ golden checks cho tên chất/mã CAS trên các trang có OCR confidence thấp.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Hà Mạnh Tuấn
