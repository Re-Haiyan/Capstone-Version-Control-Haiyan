# Fresh human-labelled test set

Purpose: an independent benchmark the models have never seen.

* Collect reviews of products NOT in review_pool_10000.csv, posted after the pool was scraped.
* Aim for 600+ reviews; keep roughly the marketplace star mix (no cherry-picking).
* Two people label every row independently (annotator_1 / annotator_2); settle disagreements
  together and write the agreed label in human_sentiment.
* Report results per language (English / Tagalog / Taglish) and per platform.
* Freeze the file before scoring any model, and never tune on it.
