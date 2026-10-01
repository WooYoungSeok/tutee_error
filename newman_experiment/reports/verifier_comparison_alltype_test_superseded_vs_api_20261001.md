# Verifier comparison on the SFT test pairs

Created 2026-10-01T13:43:32+09:00 (Asia/Seoul). Test data sha256 `af37b79709764b2170606f1274961408dbb9e01ee03338c499a2deec0c1b7c96`, 1056 pair rows. CIs: 95% question-group bootstrap (1000). Trained checkpoints were chosen on this test split (optimistic).

| verifier | source | accuracy | macro_f1 | negative_recall | negative_false_acceptance | positive_recall | invalid_rate | pair_accuracy | accuracy 95% CI |
|---|---|---|---|---|---|---|---|---|---|
| A 1차(폐기) | `newman_experiment/outputs/_superseded/verifier_half_a_seed42_20261001_051819/test_eval/epoch-5` | 0.9138 | 0.9136 | 0.8598 | 0.1402 | 0.9678 | 0.0000 | 0.8277 | [0.8994, 0.9286] |
| B 1차(폐기) | `newman_experiment/outputs/_superseded/verifier_half_b_seed42_20261001_070425/test_eval/epoch-5` | 0.9167 | 0.9166 | 0.8996 | 0.1004 | 0.9337 | 0.0000 | 0.8371 | [0.9006, 0.9337] |
| gpt-5.6-sol | `newman_experiment/outputs/verifier_api_gpt-5.6-sol_alltype_test_seed42_20261001_134120` | 0.8040 | 0.8035 | 0.7557 | 0.2443 | 0.8523 | 0.0000 | 0.6439 | [0.7787, 0.8278] |
| gpt-5.1 | `newman_experiment/outputs/verifier_api_gpt-5.1_alltype_test_seed42_20261001_134120` | 0.7093 | 0.7050 | 0.5890 | 0.4110 | 0.8295 | 0.0000 | 0.4886 | [0.6817, 0.7368] |

Negative false acceptance by negative kind (accepted / negatives):

| verifier | same stage | different stage |
|---|---|---|
| A 1차(폐기) | 7 / 126 (0.056) | 67 / 402 (0.167) |
| B 1차(폐기) | 4 / 126 (0.032) | 49 / 402 (0.122) |
| gpt-5.6-sol | 68 / 126 (0.540) | 61 / 402 (0.152) |
| gpt-5.1 | 61 / 126 (0.484) | 156 / 402 (0.388) |

Negative false acceptance by the negative's source (same dataset as the solution or another dataset):

| verifier | other_dataset | same_dataset |
|---|---|---|
| A 1차(폐기) | 0 / 360 (0.000) | 74 / 168 (0.440) |
| B 1차(폐기) | 0 / 360 (0.000) | 53 / 168 (0.315) |
| gpt-5.6-sol | 108 / 360 (0.300) | 21 / 168 (0.125) |
| gpt-5.1 | 158 / 360 (0.439) | 59 / 168 (0.351) |

Accuracy by dataset:

| verifier | eic|GSM8K | eic|MathQA | mathclean|- | mathedu|- | stepwise|- |
|---|---|---|---|---|---|
| A 1차(폐기) | 0.925 (n=266) | 0.889 (n=262) | 0.938 (n=178) | 0.910 (n=288) | 0.919 (n=62) |
| B 1차(폐기) | 0.932 (n=266) | 0.931 (n=262) | 0.933 (n=178) | 0.885 (n=288) | 0.887 (n=62) |
| gpt-5.6-sol | 0.842 (n=266) | 0.798 (n=262) | 0.730 (n=178) | 0.837 (n=288) | 0.726 (n=62) |
| gpt-5.1 | 0.692 (n=266) | 0.645 (n=262) | 0.719 (n=178) | 0.760 (n=288) | 0.790 (n=62) |

Accuracy by target stage:

| verifier | comprehension | process_skills | reading | transformation |
|---|---|---|---|---|
| A 1차(폐기) | 0.907 (n=118) | 0.887 (n=371) | 0.902 (n=153) | 0.944 (n=414) |
| B 1차(폐기) | 0.881 (n=118) | 0.884 (n=371) | 0.961 (n=153) | 0.940 (n=414) |
| gpt-5.6-sol | 0.703 (n=118) | 0.782 (n=371) | 0.935 (n=153) | 0.804 (n=414) |
| gpt-5.1 | 0.534 (n=118) | 0.687 (n=371) | 0.804 (n=153) | 0.744 (n=414) |

Paired difference against gpt-5.6-sol (other − gpt-5.6-sol, 95% question-group bootstrap):

| verifier | accuracy | negative false acceptance | positive recall |
|---|---|---|---|
| A 1차(폐기) | +0.1098 [+0.0805, +0.1385] | -0.1042 [-0.1531, -0.0579] | +0.1155 [+0.0784, +0.1491] |
| B 1차(폐기) | +0.1127 [+0.0852, +0.1426] | -0.1439 [-0.1903, -0.1002] | +0.0814 [+0.0474, +0.1182] |
| gpt-5.1 | -0.0947 [-0.1269, -0.0640] | +0.1667 [+0.1203, +0.2128] | -0.0227 [-0.0620, +0.0193] |
