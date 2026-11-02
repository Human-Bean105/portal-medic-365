# Retrieval benchmark: chunking

123 synthetic queries, silver labels by gpt-4o (see dataset note). Run 2026-11-01.

| Configuration | hit@5 | recall@5 | precision@5 | mrr@10 | recall@10 | search_ms_mean |
|---|---|---|---|---|---|---|
| B  v1: vector, old index, cutoff 0.3 | 0.911 | 0.812 | 0.53 | 0.758 | 0.865 | 27.2 |
| hybrid weighted a=0.7, c1100_o0 | 0.951 | 0.859 | 0.569 | 0.818 | 0.898 | 47.3 |
| hybrid weighted a=0.7, c1200_o1 | 0.959 | 0.865 | 0.566 | 0.829 | 0.9 | 47.2 |
| hybrid weighted a=0.7, c1500_o1 | 0.943 | 0.851 | 0.558 | 0.817 | 0.892 | 43.5 |
| hybrid weighted a=0.7, c600_o0 | 0.927 | 0.831 | 0.611 | 0.798 | 0.888 | 69.6 |
| hybrid weighted a=0.7, c600_o1 | 0.935 | 0.839 | 0.62 | 0.817 | 0.886 | 72.3 |
| hybrid weighted a=0.7, c900_o1 | 0.943 | 0.843 | 0.598 | 0.829 | 0.89 | 53.0 |

Hit@5 by query type:

| Configuration | education | everyday | guideline | scenario | wellbeing |
|---|---|---|---|---|---|
| B  v1: vector, old index, cutoff 0.3 | 0.944 | 0.893 | 1 | 0.94 | 0.789 |
| hybrid weighted a=0.7, c1100_o0 | 0.944 | 0.893 | 1 | 1 | 0.895 |
| hybrid weighted a=0.7, c1200_o1 | 0.944 | 0.929 | 1 | 1 | 0.895 |
| hybrid weighted a=0.7, c1500_o1 | 0.944 | 0.857 | 1 | 1 | 0.895 |
| hybrid weighted a=0.7, c600_o0 | 0.889 | 0.893 | 0.875 | 0.98 | 0.895 |
| hybrid weighted a=0.7, c600_o1 | 0.889 | 0.893 | 0.875 | 0.98 | 0.947 |
| hybrid weighted a=0.7, c900_o1 | 0.889 | 0.893 | 0.875 | 1 | 0.947 |
