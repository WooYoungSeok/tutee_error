# Run comparison — v1__gpt-5.4-mini__dev vs v2__gpt-5.4-mini__dev

Cases compared: 40

| | v1__gpt-5.4-mini__dev | v2__gpt-5.4-mini__dev |
| --- | --- | --- |
| prompt version | v1 | v2 |
| prompt sha256 | 1b3c182347176be6 | 15f304a7be10cace |
| model | gpt-5.4-mini | gpt-5.4-mini |
| cases with a description | 40 | 37 |
| median description words | 7 | 10 |
| descriptions outside 5-15 words | 2 | 3 |
| shares an uncommon question token | 12 | 16 |
| evidence_quote found verbatim | 30 | 37 |
| token usage | {'input_tokens': 25028, 'output_tokens': 2286, 'total_tokens': 27314} | {'input_tokens': 72908, 'output_tokens': 2146, 'total_tokens': 75054} |
| processing status | {'ok': 40} | {'ok': 38, 'json_parse_error': 2} |
| model status | {'ok': 38, 'ambiguous': 1, 'label_conflict': 1} | {'ok': 37, '(none)': 2, 'label_conflict': 1} |

## Status changes (5)

| dataset | sample_id | label | a | b |
| --- | --- | --- | --- | --- |
| mathclean | mathclean:49d0c9b1827cc310 | logic error | ok | None |
| mathclean | mathclean:58c90e44dcbf9643 | computing error | ok | None |
| mathclean | mathclean:6c8605b2eb64ed2b | expression error | ambiguous | ok |
| mathedu | mathedu:94d996d1af0f0a3f | Lack of necessary mathematical concepts | ok | label_conflict |
| stepwise | stepwise:a4cfc51315961b61 | Calculation error easily solved by a calculator | label_conflict | ok |

## Descriptions side by side

### eic

- **referencing_context_value_error**
  - v1__gpt-5.4-mini__dev: Uses an incorrect value from the problem context  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses the wrong cost value from the problem context  `[ok]`
- **unit_conversion_error**
  - v1__gpt-5.4-mini__dev: Converts time units incorrectly  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses the wrong time conversion between hours and minutes  `[ok]`
- **operator_error**
  - v1__gpt-5.4-mini__dev: Uses multiplication instead of a percentage decrease  `[ok]`
  - v2__gpt-5.4-mini__dev: Applies the percentage as a multiplication factor instead of a 10% decrease  `[ok]`
- **calculation_error**
  - v1__gpt-5.4-mini__dev: Arithmetic addition error  `[ok]`
  - v2__gpt-5.4-mini__dev: Makes an arithmetic addition error  `[ok]`
- **missing_step**
  - v1__gpt-5.4-mini__dev: Skips reducing to the remaining amount before taking a fraction  `[ok]`
  - v2__gpt-5.4-mini__dev: Applies the fraction to the original amount instead of the remainder  `[ok]`
- **adding_irrelevant_information**
  - v1__gpt-5.4-mini__dev: Adds unrelated information to the profit calculation  `[ok]`
  - v2__gpt-5.4-mini__dev: Includes an irrelevant expense not stated in the problem  `[ok]`
- **adding_irrelevant_information**
  - v1__gpt-5.4-mini__dev: Adds an irrelevant bonus not in the problem  `[ok]`
  - v2__gpt-5.4-mini__dev: Adds an unsupported bonus not given in the problem  `[ok]`
- **counting_error**
  - v1__gpt-5.4-mini__dev: Miscounts the number of days  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses the wrong number of days when scaling a daily total to a week  `[ok]`
- **confusing_formula_error**
  - v1__gpt-5.4-mini__dev: Uses perimeter-style addition instead of area multiplication  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses perimeter-style addition instead of area multiplication  `[ok]`
- **referencing_previous_step_value_error**
  - v1__gpt-5.4-mini__dev: Uses an earlier step’s value as if it were the current quantity  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses the original supply duration instead of the remaining food after the first period  `[ok]`

### mathclean

- **computing error**
  - v1__gpt-5.4-mini__dev: Applies the weekly increase repeatedly with the wrong compounding pattern  `[ok]`
  - v2__gpt-5.4-mini__dev: Makes an arithmetic error in the final computation  `[ok]`
- **logic error**
  - v1__gpt-5.4-mini__dev: Misapplies alternate interior and straight-angle relationships  `[ok]`
  - v2__gpt-5.4-mini__dev: None  `[None]`
- **computing error**
  - v1__gpt-5.4-mini__dev: Misapplies the arithmetic pattern for increasing weekly amounts  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses an incorrect arithmetic formula for the growing weekly savings  `[ok]`
- **computing error**
  - v1__gpt-5.4-mini__dev: Arithmetic mistake when combining the quantities  `[ok]`
  - v2__gpt-5.4-mini__dev: Makes an arithmetic multiplication error  `[ok]`
- **computing error**
  - v1__gpt-5.4-mini__dev: Mistakenly treats every diagonal as increasing by 1  `[ok]`
  - v2__gpt-5.4-mini__dev: None  `[None]`
- **expression error**
  - v1__gpt-5.4-mini__dev: Algebraic substitution error in solving for the parameterized form  `[ambiguous]`
  - v2__gpt-5.4-mini__dev: Makes an algebraic sign or arithmetic error when solving for the intercept parameter  `[ok]`
- **logic error**
  - v1__gpt-5.4-mini__dev: Finds the new GCF by factoring the scaled numbers directly  `[ok]`
  - v2__gpt-5.4-mini__dev: Treats the increased numbers as a simple scaling, not as preserving the original common factor structure  `[ok]`
- **expression error**
  - v1__gpt-5.4-mini__dev: Includes the same ladder-climbing amounts twice  `[ok]`
  - v2__gpt-5.4-mini__dev: Adds an extra climbing amount not stated in the problem  `[ok]`
- **logic error**
  - v1__gpt-5.4-mini__dev: Ignores the decreasing time for later graves  `[ok]`
  - v2__gpt-5.4-mini__dev: Applies the time decrease independently to each grave instead of treating it as a progression for each grave type  `[ok]`
- **expression error**
  - v1__gpt-5.4-mini__dev: Uses an incorrect expression for the quantity being multiplied  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses a different quantity than the one stated in the product expression  `[ok]`

### mathedu

- **Comprehension error**
  - v1__gpt-5.4-mini__dev: Treats simple interest as a direct multiplier on principal  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses the simple-interest amount formula with the wrong time conversion  `[ok]`
- **Comprehension error**
  - v1__gpt-5.4-mini__dev: Misinterprets the age relationships among the variables  `[ok]`
  - v2__gpt-5.4-mini__dev: Sets up the age relationship with the variables reversed  `[ok]`
- **Measurement error**
  - v1__gpt-5.4-mini__dev: Uses incompatible units without converting them first  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses incompatible units without converting them first  `[ok]`
- **Careless error**
  - v1__gpt-5.4-mini__dev: Uses the wrong quantity in the area calculation  `[ok]`
  - v2__gpt-5.4-mini__dev: Makes an arithmetic error after finding the side length  `[ok]`
- **Lack of necessary mathematical concepts**
  - v1__gpt-5.4-mini__dev: Subtracts discount from present worth instead of using the required formula  `[ok]`
  - v2__gpt-5.4-mini__dev: None  `[label_conflict]`
- **Algebraic error**
  - v1__gpt-5.4-mini__dev: Incorrectly manipulates the slope equation algebraically  `[ok]`
  - v2__gpt-5.4-mini__dev: Makes an algebraic sign error when simplifying the slope equation  `[ok]`
- **Wrong mathematical operation/concept**
  - v1__gpt-5.4-mini__dev: Uses the wrong set-operation equation for overlapping groups  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses an incorrect counting equation for overlapping sets  `[ok]`
- **Arithmetical error**
  - v1__gpt-5.4-mini__dev: Makes an arithmetic multiplication error  `[ok]`
  - v2__gpt-5.4-mini__dev: Makes an arithmetic multiplication error  `[ok]`
- **Unfinished answer**
  - v1__gpt-5.4-mini__dev: Gives only one ratio part and stops before comparing amounts  `[ok]`
  - v2__gpt-5.4-mini__dev: Stops after finding one proportional share instead of comparing the two shares  `[ok]`
- **Wrong mathematical operation/concept**
  - v1__gpt-5.4-mini__dev: Adds rates and totals with incompatible quantities  `[ok]`
  - v2__gpt-5.4-mini__dev: Uses the total work done instead of the per-day work rate  `[ok]`

### stepwise

- **Reached correct solution but proceeded further**
  - v1__gpt-5.4-mini__dev: Continues reasoning after reaching the correct answer  `[ok]`
  - v2__gpt-5.4-mini__dev: Replaces a correct total with an unjustified per-person average and then rounds it down  `[ok]`
- **Missing / Wrong factual knowledge**
  - v1__gpt-5.4-mini__dev: Computes the discount amount but treats it as the sale price  `[ok]`
  - v2__gpt-5.4-mini__dev: Treats the sale price as the amount discounted rather than the amount remaining  `[ok]`
- **Extra quantity or Missing quantity**
  - v1__gpt-5.4-mini__dev: Counts one quantity twice and omits another  `[ok]`
  - v2__gpt-5.4-mini__dev: Counts an already doubled amount again when forming the total  `[ok]`
- **Misunderstanding of a question**
  - v1__gpt-5.4-mini__dev: Misreads what quantity the question asks for  `[ok]`
  - v2__gpt-5.4-mini__dev: Treats the score as the number of mistakes and sets up the wrong relationship  `[ok]`
- **Calculation error easily solved by a calculator**
  - v1__gpt-5.4-mini__dev: Applies the ratio to the wrong quantity  `[label_conflict]`
  - v2__gpt-5.4-mini__dev: Makes an arithmetic error in the final multiplication  `[ok]`
- **Unit conversion error**
  - v1__gpt-5.4-mini__dev: Treats a ratio part as if it were a whole set  `[ok]`
  - v2__gpt-5.4-mini__dev: Divides by the total ratio parts instead of the red part ratio  `[ok]`
- **Calculation error easily solved by a calculator**
  - v1__gpt-5.4-mini__dev: Arithmetic mistake in adding the amounts  `[ok]`
  - v2__gpt-5.4-mini__dev: Makes an arithmetic addition error when totaling the amounts  `[ok]`
- **Missing / Wrong factual knowledge**
  - v1__gpt-5.4-mini__dev: Uses the wrong tire count for bicycles  `[ok]`
  - v2__gpt-5.4-mini__dev: Treats the total tire count as the number of bicycles, rather than converting remaining tires to bikes correctly  `[ok]`
- **Misunderstanding of a question**
  - v1__gpt-5.4-mini__dev: Ignores the stated amount to remove and uses the remaining total  `[ok]`
  - v2__gpt-5.4-mini__dev: Subtracts buckets from the tub capacity instead of the filled amount  `[ok]`
- **Extra quantity or Missing quantity**
  - v1__gpt-5.4-mini__dev: Adds an extra quantity not asked for  `[ok]`
  - v2__gpt-5.4-mini__dev: Counts a partial-wall time as if it applied to every wall, then adds an unnecessary full-room total  `[ok]`

Counts and flags above are descriptive only. Which description is better is a human judgement; fill in `review_which_is_better` in the CSV.
