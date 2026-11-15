| Run | mix / loss / lr / epochs / seed | rows | before: market val, FiReCS val (macro F1) | epoch results: market val macro F1 (neutral F1, neg recall) / FiReCS val | selected epoch | minutes |
|---|---|---:|---|---|---:|---:|
| b_firecs_s1 | firecs / ce / 2e-05 / 2 / 1 | 6608 | 0.635, 0.647 | e1: 0.625 (0.29, 0.71) / 0.823; e2: 0.643 (0.34, 0.68) / 0.856 | 2 | 31 |
| c1_mix_ce_s1 | firecs+market / ce / 2e-05 / 2 / 1 | 9743 | 0.635, 0.647 | e1: 0.618 (0.24, 0.77) / 0.835; e2: 0.659 (0.35, 0.79) / 0.847 | 2 | 53 |
| c1_mix_ce_s2 | firecs+market / ce / 2e-05 / 2 / 2 | 9743 | 0.635, 0.647 | e1: 0.669 (0.35, 0.81) / 0.846; e2: 0.663 (0.35, 0.80) / 0.847 | 1 | 43 |
| c1_mix_ce_s3 | firecs+market / ce / 2e-05 / 2 / 3 | 9743 | 0.635, 0.647 | e1: 0.676 (0.41, 0.77) / 0.858; e2: 0.661 (0.36, 0.78) / 0.850 | 1 | 49 |
| c2_mix_weighted_s1 | firecs+market / weighted / 2e-05 / 2 / 1 | 9743 | 0.635, 0.647 | e1: 0.637 (0.29, 0.77) / 0.841; e2: 0.665 (0.37, 0.79) / 0.849 | 2 | 58 |
| d1_mix_ce_rep2_s1 | firecs+market / ce / 2e-05 / 2 / 1, repeat 2 | 12878 | 0.635, 0.647 | e1: 0.685 (0.40, 0.81) / 0.837; e2: 0.675 (0.40, 0.81) / 0.842 | 1 | 73 |
