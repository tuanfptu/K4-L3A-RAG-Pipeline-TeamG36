# Local retrieval benchmark

Dataset: 16 grounded questions · top-k: 5
Embedding: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` · reranker: `gemini-or-safe-fallback`

| Strategy | Source hit@k | MRR | Context token recall | Avg latency |
| --- | ---: | ---: | ---: | ---: |
| Semantic | 0.938 | 0.887 | 0.693 | 1714.0 ms |
| Hybrid + RRF | 1.000 | 0.958 | 0.717 | 1743.3 ms |
| Hybrid + Neural Reranker | 1.000 | 0.958 | 0.717 | 2752.7 ms |

Source hit and MRR use the expected corpus source ID. Context token recall measures how many normalized tokens from the expected context appear in the retrieved top-k chunks.
