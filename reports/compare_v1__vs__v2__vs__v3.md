# Run comparison — v1__gpt-5.4-mini__dev, v2__gpt-5.4-mini__dev, v3__gpt-5.4-mini__dev

Cases compared: 40

| | v1 | v2 | v3 |
| --- | --- | --- | --- |
| prompt version | v1 | v2 | v3 |
| prompt sha256 | 1b3c182347176be6 | 15f304a7be10cace | 86e57f4075105fa3 |
| model | gpt-5.4-mini | gpt-5.4-mini | gpt-5.4-mini |
| cases with a description | 40 | 37 | 40 |
| median description words | 7 | 10 | 9 |
| descriptions outside 5-15 words | 2 | 3 | 1 |
| shares an uncommon question token | 12 | 16 | 12 |
| evidence_quote found verbatim | 30 | 37 | 37 |
| processing status | {'ok': 40} | {'ok': 38, 'json_parse_error': 2} | {'ok': 40} |
| model status | {'ok': 38, 'ambiguous': 1, 'label_conflict': 1} | {'ok': 37, '(none)': 2, 'label_conflict': 1} | {'ok': 39, 'label_conflict': 1} |
| token usage | {'input_tokens': 25028, 'output_tokens': 2286, 'total_tokens': 27314} | {'input_tokens': 72908, 'output_tokens': 2146, 'total_tokens': 75054} | {'input_tokens': 40708, 'output_tokens': 2024, 'total_tokens': 42732} |

## Cases where the status differs between runs (6)

| dataset | sample_id | label | v1 | v2 | v3 |
| --- | --- | --- | --- | --- | --- |
| mathclean | mathclean:49d0c9b1827cc310 | logic error | ok | None | ok |
| mathclean | mathclean:58c90e44dcbf9643 | computing error | ok | None | ok |
| mathclean | mathclean:6c8605b2eb64ed2b | expression error | ambiguous | ok | ok |
| mathclean | mathclean:761b74e99ae62496 | logic error | ok | ok | label_conflict |
| mathedu | mathedu:94d996d1af0f0a3f | Lack of necessary mathematical concepts | ok | label_conflict | ok |
| stepwise | stepwise:a4cfc51315961b61 | Calculation error easily solved by a calculator | label_conflict | ok | ok |

## Descriptions side by side

### eic

- **referencing_context_value_error**
  - v1: Uses an incorrect value from the problem context  `[ok]`
  - v2: Uses the wrong cost value from the problem context  `[ok]`
  - v3: Uses the wrong cost value for the seeds  `[ok]`
- **unit_conversion_error**
  - v1: Converts time units incorrectly  `[ok]`
  - v2: Uses the wrong time conversion between hours and minutes  `[ok]`
  - v3: Uses an incorrect time-unit conversion  `[ok]`
- **operator_error**
  - v1: Uses multiplication instead of a percentage decrease  `[ok]`
  - v2: Applies the percentage as a multiplication factor instead of a 10% decrease  `[ok]`
  - v3: Makes an arithmetic operator error in applying the percent reduction  `[ok]`
- **calculation_error**
  - v1: Arithmetic addition error  `[ok]`
  - v2: Makes an arithmetic addition error  `[ok]`
  - v3: Makes an arithmetic addition error  `[ok]`
- **missing_step**
  - v1: Skips reducing to the remaining amount before taking a fraction  `[ok]`
  - v2: Applies the fraction to the original amount instead of the remainder  `[ok]`
  - v3: Applies a fraction to the original amount instead of the remainder  `[ok]`
- **adding_irrelevant_information**
  - v1: Adds unrelated information to the profit calculation  `[ok]`
  - v2: Includes an irrelevant expense not stated in the problem  `[ok]`
  - v3: Introduces an irrelevant expense not given in the problem  `[ok]`
- **adding_irrelevant_information**
  - v1: Adds an irrelevant bonus not in the problem  `[ok]`
  - v2: Adds an unsupported bonus not given in the problem  `[ok]`
  - v3: Introduces an extra bonus not given in the problem  `[ok]`
- **counting_error**
  - v1: Miscounts the number of days  `[ok]`
  - v2: Uses the wrong number of days when scaling a daily total to a week  `[ok]`
  - v3: Uses the wrong number of days in the total  `[ok]`
- **confusing_formula_error**
  - v1: Uses perimeter-style addition instead of area multiplication  `[ok]`
  - v2: Uses perimeter-style addition instead of area multiplication  `[ok]`
  - v3: Uses perimeter instead of area  `[ok]`
- **referencing_previous_step_value_error**
  - v1: Uses an earlier step’s value as if it were the current quantity  `[ok]`
  - v2: Uses the original supply duration instead of the remaining food after the first period  `[ok]`
  - v3: Applies the reduced consumption rate to the remaining supply incorrectly  `[ok]`

### mathclean

- **computing error**
  - v1: Applies the weekly increase repeatedly with the wrong compounding pattern  `[ok]`
  - v2: Makes an arithmetic error in the final computation  `[ok]`
  - v3: Makes an arithmetic calculation error  `[ok]`
- **logic error**
  - v1: Misapplies alternate interior and straight-angle relationships  `[ok]`
  - v2: None  `[None]`
  - v3: Confuses the interior angle with its supplementary angle  `[ok]`
- **computing error**
  - v1: Misapplies the arithmetic pattern for increasing weekly amounts  `[ok]`
  - v2: Uses an incorrect arithmetic formula for the growing weekly savings  `[ok]`
  - v3: Applies the weekly increase as repeated addition over the full year instead of a per-week savings pattern  `[ok]`
- **computing error**
  - v1: Arithmetic mistake when combining the quantities  `[ok]`
  - v2: Makes an arithmetic multiplication error  `[ok]`
  - v3: Makes an arithmetic multiplication error  `[ok]`
- **computing error**
  - v1: Mistakenly treats every diagonal as increasing by 1  `[ok]`
  - v2: None  `[None]`
  - v3: Counts diagonals with the wrong multiplicities  `[ok]`
- **expression error**
  - v1: Algebraic substitution error in solving for the parameterized form  `[ambiguous]`
  - v2: Makes an algebraic sign or arithmetic error when solving for the intercept parameter  `[ok]`
  - v3: Makes an algebraic error when solving for the parameter  `[ok]`
- **logic error**
  - v1: Finds the new GCF by factoring the scaled numbers directly  `[ok]`
  - v2: Treats the increased numbers as a simple scaling, not as preserving the original common factor structure  `[ok]`
  - v3: Stops after finding the new GCF without comparing it to the original factor  `[label_conflict]`
- **expression error**
  - v1: Includes the same ladder-climbing amounts twice  `[ok]`
  - v2: Adds an extra climbing amount not stated in the problem  `[ok]`
  - v3: Adds the climbers’ totals instead of combining ladder lengths correctly  `[ok]`
- **logic error**
  - v1: Ignores the decreasing time for later graves  `[ok]`
  - v2: Applies the time decrease independently to each grave instead of treating it as a progression for each grave type  `[ok]`
  - v3: Stops after summing the individual grave times without checking the changing sequence  `[ok]`
- **expression error**
  - v1: Uses an incorrect expression for the quantity being multiplied  `[ok]`
  - v2: Uses a different quantity than the one stated in the product expression  `[ok]`
  - v3: Uses the wrong quantity from the problem  `[ok]`

### mathedu

- **Comprehension error**
  - v1: Treats simple interest as a direct multiplier on principal  `[ok]`
  - v2: Uses the simple-interest amount formula with the wrong time conversion  `[ok]`
  - v3: Applies simple interest as a linear percentage increase  `[ok]`
- **Comprehension error**
  - v1: Misinterprets the age relationships among the variables  `[ok]`
  - v2: Sets up the age relationship with the variables reversed  `[ok]`
  - v3: Sets up the age relationship with the variables reversed  `[ok]`
- **Measurement error**
  - v1: Uses incompatible units without converting them first  `[ok]`
  - v2: Uses incompatible units without converting them first  `[ok]`
  - v3: Fails to convert measurements to a common unit before calculating  `[ok]`
- **Careless error**
  - v1: Uses the wrong quantity in the area calculation  `[ok]`
  - v2: Makes an arithmetic error after finding the side length  `[ok]`
  - v3: Uses the wrong dimension when computing the fencing length  `[ok]`
- **Lack of necessary mathematical concepts**
  - v1: Subtracts discount from present worth instead of using the required formula  `[ok]`
  - v2: None  `[label_conflict]`
  - v3: Stops after finding the present worth instead of the banker’s discount  `[ok]`
- **Algebraic error**
  - v1: Incorrectly manipulates the slope equation algebraically  `[ok]`
  - v2: Makes an algebraic sign error when simplifying the slope equation  `[ok]`
  - v3: Makes an arithmetic sign error when simplifying the equation  `[ok]`
- **Wrong mathematical operation/concept**
  - v1: Uses the wrong set-operation equation for overlapping groups  `[ok]`
  - v2: Uses an incorrect counting equation for overlapping sets  `[ok]`
  - v3: Miscalculates the disjoint categories by subtracting the overlap incorrectly  `[ok]`
- **Arithmetical error**
  - v1: Makes an arithmetic multiplication error  `[ok]`
  - v2: Makes an arithmetic multiplication error  `[ok]`
  - v3: Makes an arithmetic multiplication error  `[ok]`
- **Unfinished answer**
  - v1: Gives only one ratio part and stops before comparing amounts  `[ok]`
  - v2: Stops after finding one proportional share instead of comparing the two shares  `[ok]`
  - v3: Stops at an intermediate result before finding the difference  `[ok]`
- **Wrong mathematical operation/concept**
  - v1: Adds rates and totals with incompatible quantities  `[ok]`
  - v2: Uses the total work done instead of the per-day work rate  `[ok]`
  - v3: Adds rates using the wrong quantity as the common reference  `[ok]`

### stepwise

- **Reached correct solution but proceeded further**
  - v1: Continues reasoning after reaching the correct answer  `[ok]`
  - v2: Replaces a correct total with an unjustified per-person average and then rounds it down  `[ok]`
  - v3: Stops at an intermediate average instead of the total quantity  `[ok]`
- **Missing / Wrong factual knowledge**
  - v1: Computes the discount amount but treats it as the sale price  `[ok]`
  - v2: Treats the sale price as the amount discounted rather than the amount remaining  `[ok]`
  - v3: Applies the discount as if it were the remaining price, not the reduction  `[ok]`
- **Extra quantity or Missing quantity**
  - v1: Counts one quantity twice and omits another  `[ok]`
  - v2: Counts an already doubled amount again when forming the total  `[ok]`
  - v3: Double-counts the already combined total  `[ok]`
- **Misunderstanding of a question**
  - v1: Misreads what quantity the question asks for  `[ok]`
  - v2: Treats the score as the number of mistakes and sets up the wrong relationship  `[ok]`
  - v3: Introduces an unsupported inequality instead of using the given relationship  `[ok]`
- **Calculation error easily solved by a calculator**
  - v1: Applies the ratio to the wrong quantity  `[label_conflict]`
  - v2: Makes an arithmetic error in the final multiplication  `[ok]`
  - v3: Makes an arithmetic multiplication error  `[ok]`
- **Unit conversion error**
  - v1: Treats a ratio part as if it were a whole set  `[ok]`
  - v2: Divides by the total ratio parts instead of the red part ratio  `[ok]`
  - v3: Applies the ratio to the total instead of the given part  `[ok]`
- **Calculation error easily solved by a calculator**
  - v1: Arithmetic mistake in adding the amounts  `[ok]`
  - v2: Makes an arithmetic addition error when totaling the amounts  `[ok]`
  - v3: Makes an arithmetic addition error in combining the quantities  `[ok]`
- **Missing / Wrong factual knowledge**
  - v1: Uses the wrong tire count for bicycles  `[ok]`
  - v2: Treats the total tire count as the number of bicycles, rather than converting remaining tires to bikes correctly  `[ok]`
  - v3: Uses the wrong reference quantity for the total number of tires  `[ok]`
- **Misunderstanding of a question**
  - v1: Ignores the stated amount to remove and uses the remaining total  `[ok]`
  - v2: Subtracts buckets from the tub capacity instead of the filled amount  `[ok]`
  - v3: Substitutes a smaller intermediate amount for the amount used per bath  `[ok]`
- **Extra quantity or Missing quantity**
  - v1: Adds an extra quantity not asked for  `[ok]`
  - v2: Counts a partial-wall time as if it applied to every wall, then adds an unnecessary full-room total  `[ok]`
  - v3: Includes an extra quantity beyond the remaining wallpaper  `[ok]`

Counts and flags above are descriptive only. Which description is better is a human judgement; fill in `review_which_is_better` in the CSV.
