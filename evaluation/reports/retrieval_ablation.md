# Retrieval ablation: analyzer query and reranking

Production retriever (hybrid weighted, alpha 0.7), 135 queries, rerank pool 15.

| Configuration | hit@5 | recall@5 | precision@5 | mrr@10 | recall@10 | education | everyday | guideline | scenario | wellbeing |
|---|---|---|---|---|---|---|---|---|---|---|
| v1 rewrite | 0.943 | 0.843 | 0.598 | 0.829 | 0.89 | 0.889 | 0.893 | 0.875 | 1 | 0.947 |
| v1 rewrite + rerank 15x450 | 0.951 | 0.847 | 0.646 | 0.877 | 0.898 | 0.944 | 0.893 | 0.875 | 1 | 0.947 |
| analyzer | 0.935 | 0.818 | 0.579 | 0.809 | 0.928 | 0.889 | 0.929 | 0.75 | 0.98 | 0.947 |
| analyzer + rerank 15x450 | 0.967 | 0.873 | 0.647 | 0.853 | 0.93 | 0.944 | 0.929 | 0.875 | 1 | 1 |
| analyzer + rerank 10x300 | 0.959 | 0.854 | 0.615 | 0.85 | 0.883 | 0.944 | 0.929 | 0.875 | 0.98 | 1 |
