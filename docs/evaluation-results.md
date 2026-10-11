| Configuration | Hit@1 | Hit@5 | Hit@10 | MRR@10 | Recall@10 | p50 latency |
|---|---|---|---|---|---|---|
| BM25 only | 0.09 | 0.30 | 0.36 | 0.16 | 0.33 | 0 ms |
| Dense only | 0.06 | 0.33 | 0.39 | 0.17 | 0.39 | 6 ms |
| Hybrid, RRF (k=60) | 0.06 | 0.42 | 0.58 | 0.20 | 0.53 | 6 ms |
| Hybrid, convex (alpha=0.3) | 0.09 | 0.36 | 0.42 | 0.19 | 0.41 | 6 ms |
| Hybrid, convex (alpha=0.5) | 0.15 | 0.33 | 0.55 | 0.24 | 0.52 | 6 ms |
| Hybrid, convex (alpha=0.7) | 0.12 | 0.36 | 0.45 | 0.21 | 0.45 | 6 ms |
| Hybrid, RRF, without scope detection | 0.09 | 0.33 | 0.42 | 0.18 | 0.42 | 6 ms |
