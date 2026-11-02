# Evidence sufficiency calibration

Answerable queries: per evidence status, the number of queries and the share whose top 5 passages include a labeled primary topic (hit@5) or any relevant topic. Out-of-scope queries (nothing relevant exists in the knowledge base) are counted separately: ideally they are never rated sufficient.

| Status (from reranker grades) | Answerable queries | Hit@5 (primary) | Any relevant topic in top 5 | Out-of-scope queries |
|---|---|---|---|---|
| sufficient | 117 | 0.983 | 0.991 | 1 |
| partial | 5 | 0.8 | 0.8 | 6 |
| insufficient | 1 | 0 | 0 | 1 |
| none | 0 | None | None | 4 |

Out-of-scope queries and their status: o1=partial, o2=partial, o3=partial, o4=none, o5=none, o6=partial, o7=partial, o8=none, o9=partial, o10=insufficient, o11=sufficient, o12=none

For comparison, v1's signal: the top passage's cosine similarity (same queries, before reranking).

| Top cosine | Queries | Hit@5 (primary) |
|---|---|---|
| 0.0-0.4 | 0 | None |
| 0.4-0.5 | 15 | 0.933 |
| 0.5-0.6 | 53 | 0.962 |
| 0.6-1.0 | 55 | 0.982 |

Queries rated sufficient without a primary topic in the top 5: ['q24', 'q70']
