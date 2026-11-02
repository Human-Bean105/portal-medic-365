# Retrieval benchmark: retrievers

123 synthetic queries, silver labels by gpt-4o (see dataset note). Run 2026-11-01.

| Configuration | hit@5 | recall@5 | precision@5 | mrr@10 | recall@10 | search_ms_mean |
|---|---|---|---|---|---|---|
| B  v1: vector, old index, cutoff 0.3 | 0.911 | 0.812 | 0.53 | 0.758 | 0.865 | 27.0 |
| vector, new index | 0.919 | 0.812 | 0.561 | 0.796 | 0.865 | 51.6 |
| bm25, new index | 0.821 | 0.713 | 0.47 | 0.661 | 0.752 | 1.6 |
| hybrid rrf a=0.5 | 0.927 | 0.827 | 0.584 | 0.788 | 0.888 | 53.5 |
| hybrid rrf a=0.7 | 0.935 | 0.831 | 0.589 | 0.792 | 0.881 | 53.0 |
| hybrid weighted a=0.5 | 0.927 | 0.822 | 0.587 | 0.801 | 0.888 | 53.8 |
| hybrid weighted a=0.7 | 0.943 | 0.843 | 0.598 | 0.829 | 0.89 | 53.6 |
| hybrid rrf a=0.5 + wellbeing boost | 0.927 | 0.827 | 0.585 | 0.787 | 0.888 | 54.1 |
| hybrid weighted a=0.8 | 0.943 | 0.843 | 0.6 | 0.816 | 0.89 | 53.8 |
| hybrid weighted a=0.7 + wellbeing boost | 0.943 | 0.843 | 0.6 | 0.832 | 0.892 | 52.7 |
| hybrid weighted a=0.7, wellbeing a=0.9 | 0.943 | 0.843 | 0.598 | 0.829 | 0.89 | 53.0 |
| hybrid weighted a=0.7, wellbeing a=0.9 + boost | 0.943 | 0.843 | 0.6 | 0.832 | 0.892 | 53.6 |

Hit@5 by query type:

| Configuration | education | everyday | guideline | scenario | wellbeing |
|---|---|---|---|---|---|
| B  v1: vector, old index, cutoff 0.3 | 0.944 | 0.893 | 1 | 0.94 | 0.789 |
| vector, new index | 0.944 | 0.857 | 0.875 | 0.94 | 0.947 |
| bm25, new index | 0.833 | 0.786 | 0.875 | 0.92 | 0.579 |
| hybrid rrf a=0.5 | 0.833 | 0.893 | 0.875 | 0.98 | 0.947 |
| hybrid rrf a=0.7 | 0.889 | 0.857 | 0.875 | 1 | 0.947 |
| hybrid weighted a=0.5 | 0.833 | 0.893 | 0.875 | 0.98 | 0.947 |
| hybrid weighted a=0.7 | 0.889 | 0.893 | 0.875 | 1 | 0.947 |
| hybrid rrf a=0.5 + wellbeing boost | 0.833 | 0.893 | 0.875 | 0.98 | 0.947 |
| hybrid weighted a=0.8 | 0.944 | 0.857 | 0.875 | 1 | 0.947 |
| hybrid weighted a=0.7 + wellbeing boost | 0.889 | 0.893 | 0.875 | 1 | 0.947 |
| hybrid weighted a=0.7, wellbeing a=0.9 | 0.889 | 0.893 | 0.875 | 1 | 0.947 |
| hybrid weighted a=0.7, wellbeing a=0.9 + boost | 0.889 | 0.893 | 0.875 | 1 | 0.947 |
