| Configuration | Hit@1 | Hit@5 | Hit@10 | MRR@10 | Recall@10 | p50 latency |
|---|---|---|---|---|---|---|
| BM25 only | 0.15 | 0.42 | 0.58 | 0.27 | 0.55 | 0 ms |
| Dense only | 0.09 | 0.39 | 0.55 | 0.23 | 0.55 | 6 ms |
| Hybrid, RRF (k=60) | 0.18 | 0.58 | 0.67 | 0.32 | 0.64 | 6 ms |
| Hybrid, convex (alpha=0.3) | 0.15 | 0.48 | 0.55 | 0.27 | 0.52 | 6 ms |
| Hybrid, convex (alpha=0.5) | 0.15 | 0.42 | 0.64 | 0.28 | 0.61 | 6 ms |
| Hybrid, convex (alpha=0.7) | 0.12 | 0.48 | 0.58 | 0.26 | 0.58 | 6 ms |
| Hybrid, RRF, without query expansion | 0.06 | 0.42 | 0.58 | 0.20 | 0.53 | 6 ms |
| Hybrid, RRF, without scope detection | 0.15 | 0.45 | 0.58 | 0.28 | 0.56 | 7 ms |
