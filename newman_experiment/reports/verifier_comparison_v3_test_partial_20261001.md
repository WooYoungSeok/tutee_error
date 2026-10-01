# Verifier comparison on the SFT test pairs

Created 2026-10-01T20:11:19+09:00 (Asia/Seoul). Test data sha256 `0aac89ffa7e3345a575813776acad16fbd3441986a6ef4e21334576c6dc82cc5`, 1584 pair rows. CIs: 95% question-group bootstrap (1000). Trained checkpoints were chosen on this test split (optimistic).

| verifier | source | accuracy | macro_f1 | negative_recall | negative_false_acceptance | positive_recall | invalid_rate | pair_accuracy | accuracy 95% CI |
|---|---|---|---|---|---|---|---|---|---|
| A 3차 | `newman_experiment/outputs/verifier_half_a_v3_seed42_20261001_171232/test_eval/epoch-5` | 0.8662 | 0.8508 | 0.8902 | 0.1098 | 0.8182 | 0.0000 | 0.6856 | [0.8459, 0.8846] |
| A 2차 | `newman_experiment/outputs/verifier_half_a_seed42_20261001_131155/test_eval_v3_test/epoch-5` | 0.7090 | 0.6971 | 0.6799 | 0.3201 | 0.7670 | 0.0000 | 0.4470 | [0.6783, 0.7345] |
| B 2차 | `newman_experiment/outputs/verifier_half_b_seed42_20261001_145835/test_eval_v3_test/epoch-5` | 0.7620 | 0.7450 | 0.7652 | 0.2348 | 0.7557 | 0.0000 | 0.5133 | [0.7364, 0.7871] |
| gpt-5.6-sol | `newman_experiment/outputs/verifier_api_gpt-5.6-sol_v3_test_seed42_20261001_142734` | 0.8258 | 0.8131 | 0.8144 | 0.1856 | 0.8485 | 0.0000 | 0.6080 | [0.8053, 0.8460] |
| gpt-5.1 | `newman_experiment/outputs/verifier_api_gpt-5.1_v3_test_seed42_20261001_142734` | 0.6237 | 0.6201 | 0.5407 | 0.4593 | 0.7898 | 0.0000 | 0.2576 | [0.5975, 0.6510] |

Negative false acceptance by negative kind (accepted / negatives):

| verifier | same stage | different stage |
|---|---|---|
| A 3차 | 6 / 55 (0.109) | 110 / 1001 (0.110) |
| A 2차 | 13 / 55 (0.236) | 325 / 1001 (0.325) |
| B 2차 | 9 / 55 (0.164) | 239 / 1001 (0.239) |
| gpt-5.6-sol | 21 / 55 (0.382) | 175 / 1001 (0.175) |
| gpt-5.1 | 30 / 55 (0.545) | 455 / 1001 (0.455) |

Negative false acceptance by the negative's source (same dataset as the solution or another dataset):

| verifier | other_dataset | same_dataset |
|---|---|---|
| A 3차 | 0 / 528 (0.000) | 116 / 528 (0.220) |
| A 2차 | 196 / 528 (0.371) | 142 / 528 (0.269) |
| B 2차 | 147 / 528 (0.278) | 101 / 528 (0.191) |
| gpt-5.6-sol | 89 / 528 (0.169) | 107 / 528 (0.203) |
| gpt-5.1 | 259 / 528 (0.491) | 226 / 528 (0.428) |

Accuracy by dataset:

| verifier | eic|GSM8K | eic|MathQA | mathclean|- | mathedu|- | stepwise|- |
|---|---|---|---|---|---|
| A 3차 | 0.937 (n=399) | 0.924 (n=393) | 0.742 (n=267) | 0.850 (n=432) | 0.753 (n=93) |
| A 2차 | 0.679 (n=399) | 0.733 (n=393) | 0.652 (n=267) | 0.752 (n=432) | 0.699 (n=93) |
| B 2차 | 0.820 (n=399) | 0.827 (n=393) | 0.678 (n=267) | 0.706 (n=432) | 0.742 (n=93) |
| gpt-5.6-sol | 0.910 (n=399) | 0.855 (n=393) | 0.715 (n=267) | 0.819 (n=432) | 0.688 (n=93) |
| gpt-5.1 | 0.634 (n=399) | 0.603 (n=393) | 0.599 (n=267) | 0.639 (n=432) | 0.667 (n=93) |

Accuracy by target stage:

| verifier | comprehension | process_skills | reading | transformation |
|---|---|---|---|---|
| A 3차 | 0.780 (n=218) | 0.873 (n=620) | 0.949 (n=235) | 0.857 (n=511) |
| A 2차 | 0.335 (n=218) | 0.811 (n=620) | 0.911 (n=235) | 0.652 (n=511) |
| B 2차 | 0.518 (n=218) | 0.765 (n=620) | 0.932 (n=235) | 0.785 (n=511) |
| gpt-5.6-sol | 0.670 (n=218) | 0.855 (n=620) | 0.877 (n=235) | 0.834 (n=511) |
| gpt-5.1 | 0.349 (n=218) | 0.655 (n=620) | 0.753 (n=235) | 0.644 (n=511) |

Paired difference against gpt-5.6-sol (other − gpt-5.6-sol, 95% question-group bootstrap):

| verifier | accuracy | negative false acceptance | positive recall |
|---|---|---|---|
| A 3차 | +0.0404 [+0.0182, +0.0617] | -0.0758 [-0.0998, -0.0511] | -0.0303 [-0.0712, +0.0096] |
| A 2차 | -0.1168 [-0.1477, -0.0871] | +0.1345 [+0.1012, +0.1695] | -0.0814 [-0.1236, -0.0396] |
| B 2차 | -0.0638 [-0.0894, -0.0378] | +0.0492 [+0.0179, +0.0792] | -0.0928 [-0.1331, -0.0529] |
| gpt-5.1 | -0.2020 [-0.2296, -0.1753] | +0.2737 [+0.2393, +0.3081] | -0.0587 [-0.1007, -0.0172] |
