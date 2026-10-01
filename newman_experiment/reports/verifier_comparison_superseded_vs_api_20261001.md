# Verifier comparison on the SFT test pairs

Created 2026-10-01T13:43:33+09:00 (Asia/Seoul). Test data sha256 `3c95e572aa6e3d8f08c45a51243d5ae58bc84be821a0d57352ef2028198aa029`, 1056 pair rows. CIs: 95% question-group bootstrap (1000). Trained checkpoints were chosen on this test split (optimistic).

| verifier | source | accuracy | macro_f1 | negative_recall | negative_false_acceptance | positive_recall | invalid_rate | pair_accuracy | accuracy 95% CI |
|---|---|---|---|---|---|---|---|---|---|
| A 1차(폐기) | `newman_experiment/outputs/_superseded/verifier_half_a_seed42_20261001_051819/test_eval_same_dataset_negatives/epoch-5` | 0.7055 | 0.6837 | 0.4432 | 0.5568 | 0.9678 | 0.0000 | 0.4242 | [0.6817, 0.7278] |
| B 1차(폐기) | `newman_experiment/outputs/_superseded/verifier_half_b_seed42_20261001_070425/test_eval_same_dataset_negatives/epoch-5` | 0.7443 | 0.7346 | 0.5530 | 0.4470 | 0.9356 | 0.0000 | 0.5133 | [0.7193, 0.7685] |
| gpt-5.6-sol | `newman_experiment/outputs/verifier_api_gpt-5.6-sol_seed42_20261001_132300` | 0.8277 | 0.8276 | 0.8049 | 0.1951 | 0.8504 | 0.0000 | 0.7254 | [0.8011, 0.8521] |
| gpt-5.1 | `newman_experiment/outputs/verifier_api_gpt-5.1_seed42_20261001_132300` | 0.6998 | 0.6962 | 0.5909 | 0.4091 | 0.8087 | 0.0000 | 0.5000 | [0.6707, 0.7285] |

Negative false acceptance by negative kind (accepted / negatives):

| verifier | same stage | different stage |
|---|---|---|
| A 1차(폐기) | 17 / 55 (0.309) | 277 / 473 (0.586) |
| B 1차(폐기) | 13 / 55 (0.236) | 223 / 473 (0.471) |
| gpt-5.6-sol | 21 / 55 (0.382) | 82 / 473 (0.173) |
| gpt-5.1 | 24 / 55 (0.436) | 192 / 473 (0.406) |

Negative false acceptance by the negative's source (same dataset as the solution or another dataset):

| verifier | same_dataset |
|---|---|
| A 1차(폐기) | 294 / 528 (0.557) |
| B 1차(폐기) | 236 / 528 (0.447) |
| gpt-5.6-sol | 103 / 528 (0.195) |
| gpt-5.1 | 216 / 528 (0.409) |

Accuracy by dataset:

| verifier | eic|GSM8K | eic|MathQA | mathclean|- | mathedu|- | stepwise|- |
|---|---|---|---|---|---|
| A 1차(폐기) | 0.816 (n=266) | 0.802 (n=262) | 0.500 (n=178) | 0.688 (n=288) | 0.500 (n=62) |
| B 1차(폐기) | 0.883 (n=266) | 0.878 (n=262) | 0.494 (n=178) | 0.705 (n=288) | 0.484 (n=62) |
| gpt-5.6-sol | 0.929 (n=266) | 0.878 (n=262) | 0.685 (n=178) | 0.799 (n=288) | 0.726 (n=62) |
| gpt-5.1 | 0.786 (n=266) | 0.725 (n=262) | 0.573 (n=178) | 0.674 (n=288) | 0.710 (n=62) |

Accuracy by target stage:

| verifier | comprehension | process_skills | reading | transformation |
|---|---|---|---|---|
| A 1차(폐기) | 0.539 (n=102) | 0.607 (n=392) | 0.817 (n=169) | 0.799 (n=393) |
| B 1차(폐기) | 0.578 (n=102) | 0.648 (n=392) | 0.923 (n=169) | 0.807 (n=393) |
| gpt-5.6-sol | 0.627 (n=102) | 0.837 (n=392) | 0.876 (n=169) | 0.850 (n=393) |
| gpt-5.1 | 0.569 (n=102) | 0.671 (n=392) | 0.775 (n=169) | 0.730 (n=393) |

Paired difference against gpt-5.6-sol (other − gpt-5.6-sol, 95% question-group bootstrap):

| verifier | accuracy | negative false acceptance | positive recall |
|---|---|---|---|
| A 1차(폐기) | -0.1222 [-0.1510, -0.0942] | +0.3617 [+0.3148, +0.4133] | +0.1174 [+0.0843, +0.1515] |
| B 1차(폐기) | -0.0833 [-0.1112, -0.0555] | +0.2519 [+0.2044, +0.2998] | +0.0852 [+0.0531, +0.1203] |
| gpt-5.1 | -0.1278 [-0.1586, -0.0988] | +0.2140 [+0.1685, +0.2587] | -0.0417 [-0.0812, -0.0038] |
