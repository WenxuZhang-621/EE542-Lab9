# Part 5: word-histogram embedding vs OpenAI embedding

Chunks: 1694 (data/topic/index), questions: 32, metrics from `rag.evaluate.score`. Rankings by cosine similarity over all chunks; k-means and Word2Vec seeded (42).

| Group | Method | hit@1 | hit@4 | hit@10 | recall@4 | recall@10 | MRR | vocab | fit+embed s |
|---|---|---|---|---|---|---|---|---|---|
| reference | OpenAI text-embedding-3-small (C's baseline) | 0.656 | 0.938 | 0.969 | 0.703 | 0.850 | 0.790 | – | – |
| reference | BM25 keyword search (not an embedding) | 0.531 | 0.844 | 0.875 | 0.660 | 0.733 | 0.663 | – | 0.1 |
| baseline | baseline (handout) | 0.250 | 0.438 | 0.562 | 0.273 | 0.433 | 0.349 | 3039 | 5.9 |
| sweep | K=50 | 0.094 | 0.219 | 0.344 | 0.120 | 0.259 | 0.152 | 3039 | 5.3 |
| sweep | K=100 | 0.062 | 0.250 | 0.344 | 0.175 | 0.230 | 0.165 | 3039 | 5.3 |
| sweep | K=400 | 0.219 | 0.469 | 0.562 | 0.271 | 0.381 | 0.343 | 3039 | 5.3 |
| sweep | K=800 | 0.250 | 0.344 | 0.469 | 0.253 | 0.326 | 0.294 | 3039 | 5.3 |
| sweep | N=50 | 0.125 | 0.312 | 0.438 | 0.189 | 0.279 | 0.208 | 3039 | 4.2 |
| sweep | N=200 | 0.094 | 0.344 | 0.500 | 0.255 | 0.377 | 0.197 | 3039 | 8.0 |
| sweep | CBOW instead of skip-gram | 0.281 | 0.438 | 0.531 | 0.300 | 0.416 | 0.370 | 3039 | 1.7 |
| improve | cosine (spherical) k-means | 0.188 | 0.312 | 0.469 | 0.207 | 0.331 | 0.265 | 3039 | 5.5 |
| improve | drop stop-words | 0.125 | 0.406 | 0.531 | 0.252 | 0.413 | 0.262 | 2918 | 3.7 |
| improve | IDF-weighted bins | 0.250 | 0.469 | 0.531 | 0.295 | 0.424 | 0.342 | 3039 | 5.3 |
| improve | soft assignment (3 centroids) | 0.219 | 0.438 | 0.562 | 0.267 | 0.433 | 0.315 | 3039 | 5.5 |
| improve | L2 normalisation | 0.250 | 0.438 | 0.562 | 0.273 | 0.433 | 0.349 | 3039 | 5.3 |
| improve | + mean word vector (alpha 0.5) | 0.312 | 0.500 | 0.719 | 0.345 | 0.559 | 0.413 | 3039 | 5.3 |
| improve | + mean word vector (alpha 1.0) | 0.281 | 0.500 | 0.750 | 0.350 | 0.572 | 0.404 | 3039 | 5.3 |
| improve | + mean word vector (alpha 2.0) | 0.250 | 0.500 | 0.750 | 0.374 | 0.575 | 0.384 | 3039 | 5.4 |
| hybrid | combined improvements | 0.219 | 0.438 | 0.531 | 0.294 | 0.365 | 0.323 | 2918 | 3.7 |
| hybrid | combined, K=400 | 0.312 | 0.656 | 0.688 | 0.442 | 0.533 | 0.455 | 2918 | 3.8 |
| hybrid | combined, K=400, + mean vector 0.5 | 0.344 | 0.656 | 0.688 | 0.448 | 0.541 | 0.471 | 2918 | 3.8 |
| hybrid | combined, K=400, + mean vector 1.0 (BEST) | 0.375 | 0.656 | 0.750 | 0.448 | 0.559 | 0.496 | 2918 | 3.8 |
| hybrid | combined, K=400, + mean vector 2.0 | 0.406 | 0.625 | 0.781 | 0.470 | 0.601 | 0.526 | 2918 | 3.8 |
| hybrid | combined, K=800, + mean vector 1.0 | 0.312 | 0.562 | 0.719 | 0.429 | 0.570 | 0.446 | 2918 | 4.1 |
| seeds | baseline, seed 1 | 0.094 | 0.219 | 0.312 | 0.142 | 0.246 | 0.155 | 3039 | 5.4 |
| seeds | baseline, seed 2 | 0.250 | 0.344 | 0.500 | 0.212 | 0.367 | 0.305 | 3039 | 5.3 |
| seeds | baseline, seed 3 | 0.094 | 0.312 | 0.438 | 0.184 | 0.331 | 0.199 | 3039 | 5.3 |
| seeds | BEST, seed 1 | 0.312 | 0.562 | 0.688 | 0.411 | 0.534 | 0.425 | 2918 | 3.8 |
| seeds | BEST, seed 2 | 0.281 | 0.531 | 0.719 | 0.355 | 0.559 | 0.408 | 2918 | 3.8 |
| seeds | BEST, seed 3 | 0.281 | 0.500 | 0.625 | 0.383 | 0.503 | 0.395 | 2918 | 3.8 |

## Per-question first relevant rank (OpenAI / BM25 / baseline / BEST)

| # | Question | OpenAI | BM25 | baseline | BEST |
|---|---|---|---|---|---|
| 1 | How many credit hours must an undergraduate F-1 student take each term | 1 | 1 | 6 | 1 |
| 2 | How many online or distance-learning classes can count toward an F-1 s | 1 | 1 | 1 | 1 |
| 3 | How early can a new F-1 student enter the United States before the pro | 1 | 1 | 3 | 1 |
| 4 | Under the current regulation, what is the maximum period of admission  | 2 | – | – | – |
| 5 | How many days does an F-1 student have to leave the United States afte | 2 | – | 7 | – |
| 6 | Within how many days must an F-1 student report a change of address? | 2 | 2 | 6 | 2 |
| 7 | After transferring, how soon must an F-1 student contact the DSO at th | 1 | 2 | 3 | 2 |
| 8 | If an F-1 student is outside the United States for up to five months,  | 1 | 1 | – | 4 |
| 9 | Can the F-2 spouse of an F-1 student work in the United States? | 1 | 2 | – | 3 |
| 10 | Do I need to pay the I-901 SEVIS fee again to reenter the United State | 1 | 1 | 1 | 2 |
| 11 | How many hours per week can an F-1 student work on campus while school | 1 | 1 | 3 | – |
| 12 | Can an F-1 student work on campus full-time during school breaks? | 9 | 1 | – | – |
| 13 | What is curricular practical training (CPT)? | 3 | 7 | – | – |
| 14 | Does a year of full-time CPT affect eligibility for post-completion OP | 1 | 1 | 1 | 1 |
| 15 | How many months of OPT can a student get at each degree level? | 1 | 1 | 1 | 1 |
| 16 | What is the earliest and latest time to file for post-completion OPT? | 2 | 4 | – | 4 |
| 17 | How many days of unemployment are allowed during post-completion OPT? | 2 | 1 | 1 | 1 |
| 18 | How many total days of unemployment are allowed for a student with a S | 1 | 1 | 1 | 1 |
| 19 | How long is the STEM OPT extension? | 1 | 3 | 1 | 1 |
| 20 | What must a STEM OPT employer be enrolled in? | 1 | 1 | 2 | 1 |
| 21 | Which form is the training plan for STEM OPT students? | 1 | 1 | – | 3 |
| 22 | Can I start working on OPT before my EAD arrives? | 1 | 1 | 2 | 1 |
| 23 | What is the cap-gap extension for F-1 students with an H-1B petition? | 3 | – | – | – |
| 24 | How early can an F-1 student apply for an on-campus job before classes | 1 | 2 | 2 | – |
| 25 | Is there a minimum income that requires a foreign student to file a U. | 1 | 2 | – | – |
| 26 | For how many years can a student be an exempt individual for the subst | 2 | – | 5 | 7 |
| 27 | Which form do F-1 students file to explain they are exempt individuals | – | 3 | – | 10 |
| 28 | Where do I mail Form 8843 if I do not have to file a tax return? | 1 | 1 | – | 1 |
| 29 | Can a nonresident alien student claim the standard deduction? | 1 | 1 | 1 | 2 |
| 30 | How do I get an ITIN if I cannot get a Social Security number? | 1 | 3 | – | 3 |
| 31 | Are social security and Medicare taxes withheld from an F-1 student's  | 1 | 1 | – | 1 |
| 32 | Which tax return must a nonresident alien file when engaged in a U.S.  | 2 | 3 | – | 7 |
