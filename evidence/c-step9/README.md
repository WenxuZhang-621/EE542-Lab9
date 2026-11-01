# Step 9: evaluation question set and OpenAI retrieval baseline (for B)

2026-10-28 PDT. Input: data/topic/index (1694 chunks).

- questions.draft.jsonl: 32 questions (10 on status, 14 on work, 8 on taxes), each with an evidence sentence quoted from the sources; label.txt lists the number of relevant chunks labeled for each question (1–5).
- The first labeling used the wording of only one source, which gave a baseline hit@4 of 0.78. Checking the misses showed that other sources state the same facts (for example, a web page says "20 hours per week"), so equivalent evidence sentences were added and the questions were relabeled. The rule for adding them was "every chunk that states the fact counts as relevant", not picking chunks from the retrieval results.
- baseline.txt: hit@1 0.656, hit@4 0.938, hit@10 0.969, recall@4 0.703, MRR 0.790. The 2 questions still missed in the top 4: full-time on-campus work during breaks (rank 9), and which form an exempt individual files (not in the top 10).
- For the deadline to apply for post-completion OPT, the 2026 regulation says 30 days after the program ends and the web pages say 60 days, so both statements are labeled relevant.
