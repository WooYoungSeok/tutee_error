# Run comparison — v4__gpt-5.4-mini__dev, v4__gpt-5.6-luna__dev, v4__gpt-5.6-terra__dev

Cases compared: 40

| | gpt-5.4-mini | gpt-5.6-luna | gpt-5.6-terra |
| --- | --- | --- | --- |
| prompt version | v4 | v4 | v4 |
| prompt sha256 | 28ef5467bbbac5ce | 28ef5467bbbac5ce | 28ef5467bbbac5ce |
| model | gpt-5.4-mini | gpt-5.6-luna | gpt-5.6-terra |
| cases with a description | 40 | 36 | 35 |
| median description words | 8 | 9 | 9 |
| descriptions outside 5-15 words | 2 | 0 | 0 |
| shares an uncommon question token | 16 | 12 | 12 |
| evidence_quote found verbatim | 34 | 35 | 36 |
| processing status | {'ok': 40} | {'ok': 39, 'json_parse_error': 1} | {'ok': 40} |
| model status | {'ok': 38, 'label_conflict': 2} | {'ok': 36, '(none)': 1, 'label_conflict': 3} | {'ok': 35, 'label_conflict': 5} |
| token usage | {'input_tokens': 33388, 'output_tokens': 2168, 'total_tokens': 35556} | {'input_tokens': 33388, 'output_tokens': 8536, 'total_tokens': 41924} | {'input_tokens': 33388, 'output_tokens': 3270, 'total_tokens': 36658} |

## Cases where the status differs between runs (6)

| dataset | sample_id | label | gpt-5.4-mini | gpt-5.6-luna | gpt-5.6-terra |
| --- | --- | --- | --- | --- | --- |
| mathclean | mathclean:021b0bf3e810c899 | computing error | ok | ok | label_conflict |
| mathclean | mathclean:49d0c9b1827cc310 | logic error | ok | None | ok |
| mathclean | mathclean:6c8605b2eb64ed2b | expression error | ok | label_conflict | label_conflict |
| mathclean | mathclean:8351714360a1cde0 | expression error | ok | label_conflict | label_conflict |
| mathclean | mathclean:9ac6eb03c135487d | logic error | ok | ok | label_conflict |
| stepwise | stepwise:231586f8d27166cb | Reached correct solution but proceeded further | label_conflict | ok | ok |

## Descriptions side by side

### eic

- **referencing_context_value_error**
  - gpt-5.4-mini: Uses an incorrect value for the seed cost  `[ok]`
  - gpt-5.6-luna: Uses an incorrect cost value when calculating total expenses  `[ok]`
  - gpt-5.6-terra: Uses an incorrect value from the given information.  `[ok]`
- **unit_conversion_error**
  - gpt-5.4-mini: Converts time units incorrectly  `[ok]`
  - gpt-5.6-luna: Uses an incorrect conversion between hours and minutes  `[ok]`
  - gpt-5.6-terra: Uses an incorrect conversion between hours and minutes.  `[ok]`
- **operator_error**
  - gpt-5.4-mini: Uses an invalid operation instead of taking a percent decrease  `[ok]`
  - gpt-5.6-luna: Converts a percentage incorrectly by multiplying by 100 instead of dividing by 100  `[ok]`
  - gpt-5.6-terra: Multiplies by the percentage number instead of converting it to a decimal.  `[ok]`
- **calculation_error**
  - gpt-5.4-mini: Adds the difference instead of the total  `[ok]`
  - gpt-5.6-luna: Makes an arithmetic addition error  `[ok]`
  - gpt-5.6-terra: Makes an arithmetic error when adding quantities.  `[ok]`
- **missing_step**
  - gpt-5.4-mini: Uses the original total instead of the remainder for the second part  `[ok]`
  - gpt-5.6-luna: Takes a fraction of the original total instead of the remainder  `[ok]`
  - gpt-5.6-terra: Calculates a fraction of the original amount instead of the remainder  `[ok]`
- **adding_irrelevant_information**
  - gpt-5.4-mini: Adds an irrelevant expense not in the problem  `[ok]`
  - gpt-5.6-luna: Adds an unprovided expense to the profit calculation  `[ok]`
  - gpt-5.6-terra: Introduces an unsupported expense into the profit calculation  `[ok]`
- **adding_irrelevant_information**
  - gpt-5.4-mini: Adds an unsupported extra bonus amount  `[ok]`
  - gpt-5.6-luna: Adds an unsupported bonus to the total earnings  `[ok]`
  - gpt-5.6-terra: Adds an unsupported bonus payment to the calculation  `[ok]`
- **counting_error**
  - gpt-5.4-mini: Uses the wrong number of days in the total  `[ok]`
  - gpt-5.6-luna: Counts the days from Monday to Saturday incorrectly  `[ok]`
  - gpt-5.6-terra: Uses the wrong number of days when finding a weekly total.  `[ok]`
- **confusing_formula_error**
  - gpt-5.4-mini: Uses perimeter-like addition instead of area multiplication  `[ok]`
  - gpt-5.6-luna: Uses perimeter addition instead of multiplying length by width  `[ok]`
  - gpt-5.6-terra: Uses the perimeter formula instead of the area formula  `[ok]`
- **referencing_previous_step_value_error**
  - gpt-5.4-mini: Uses an incorrect value from a previous step  `[ok]`
  - gpt-5.6-luna: Uses an incorrect value from a previous calculation  `[ok]`
  - gpt-5.6-terra: Uses a value not obtained in the previous calculation.  `[ok]`

### mathclean

- **computing error**
  - gpt-5.4-mini: Applies the weekly raise multiplicatively each week to the daily rate, rather than increasing from the current week’s earnings correctly  `[ok]`
  - gpt-5.6-luna: Reports an arithmetic result inconsistent with the implemented calculation  `[ok]`
  - gpt-5.6-terra: None  `[label_conflict]`
- **logic error**
  - gpt-5.4-mini: Adds angles that should be related by a linear pair  `[ok]`
  - gpt-5.6-luna: None  `[None]`
  - gpt-5.6-terra: Misidentifies the angle relationship and equates an angle to a sum.  `[ok]`
- **computing error**
  - gpt-5.4-mini: Computes the arithmetic progression sum incorrectly  `[ok]`
  - gpt-5.6-luna: Confuses the final term of an arithmetic sequence with its cumulative total  `[ok]`
  - gpt-5.6-terra: Confuses the final weekly amount with the total accumulated amount.  `[ok]`
- **computing error**
  - gpt-5.4-mini: Uses a fractional result instead of a whole number count  `[label_conflict]`
  - gpt-5.6-luna: None  `[label_conflict]`
  - gpt-5.6-terra: None  `[label_conflict]`
- **computing error**
  - gpt-5.4-mini: Treats increased side lengths as if all diagonals increased too  `[ok]`
  - gpt-5.6-luna: Applies only one monthly increase instead of accumulating all monthly increases  `[ok]`
  - gpt-5.6-terra: Omits several classes of diagonals from the total sum  `[ok]`
- **expression error**
  - gpt-5.4-mini: Substitutes the wrong coordinate into the parametric equations  `[ok]`
  - gpt-5.6-luna: None  `[label_conflict]`
  - gpt-5.6-terra: None  `[label_conflict]`
- **logic error**
  - gpt-5.4-mini: Computes the new common factor after scaling incorrectly  `[ok]`
  - gpt-5.6-luna: Omits larger common factors when identifying the greatest common factor  `[ok]`
  - gpt-5.6-terra: Omits shared factors and identifies a non-greatest common factor.  `[ok]`
- **expression error**
  - gpt-5.4-mini: Adds the repeated climbs instead of using the ladder length once per worker  `[ok]`
  - gpt-5.6-luna: None  `[label_conflict]`
  - gpt-5.6-terra: None  `[label_conflict]`
- **logic error**
  - gpt-5.4-mini: Treats each grave type separately instead of continuing the decreasing times across all graves  `[ok]`
  - gpt-5.6-luna: Calculates the final sum incorrectly  `[ok]`
  - gpt-5.6-terra: None  `[label_conflict]`
- **expression error**
  - gpt-5.4-mini: Uses the wrong quantity in the final multiplication  `[ok]`
  - gpt-5.6-luna: Omits the repeated frequency when calculating the weekly total  `[ok]`
  - gpt-5.6-terra: Introduces an unsupported annual conversion instead of using the weekly quantity.  `[ok]`

### mathedu

- **Comprehension error**
  - gpt-5.4-mini: Uses a simple-interest formula incorrectly by treating the rate-time product as a decimal factor  `[ok]`
  - gpt-5.6-luna: Converts a mixed number to the wrong improper fraction  `[ok]`
  - gpt-5.6-terra: Converts a mixed number to an improper fraction incorrectly.  `[ok]`
- **Comprehension error**
  - gpt-5.4-mini: Sets up the age relationship backward  `[ok]`
  - gpt-5.6-luna: Reports a related quantity instead of the requested quantity  `[ok]`
  - gpt-5.6-terra: Equates age relationships without defining all variables consistently.  `[ok]`
- **Measurement error**
  - gpt-5.4-mini: Uses inconsistent units in a measurement calculation  `[ok]`
  - gpt-5.6-luna: Fails to convert measurements to consistent units before calculating area  `[ok]`
  - gpt-5.6-terra: Divides areas expressed in incompatible measurement units.  `[ok]`
- **Careless error**
  - gpt-5.4-mini: Uses the area to infer side lengths incorrectly  `[ok]`
  - gpt-5.6-luna: Changes a given measurement during the final addition  `[ok]`
  - gpt-5.6-terra: Uses an incorrect side length when adding the fenced sides.  `[ok]`
- **Lack of necessary mathematical concepts**
  - gpt-5.4-mini: Subtracts the discount from present worth instead of using the proper discount relation  `[ok]`
  - gpt-5.6-luna: Subtracts true discount from present worth instead of calculating banker’s discount  `[ok]`
  - gpt-5.6-terra: Subtracts the discount from present worth instead of finding banker's discount.  `[ok]`
- **Algebraic error**
  - gpt-5.4-mini: Fails to isolate the variable correctly after setting up the slope equation  `[ok]`
  - gpt-5.6-luna: Makes a sign error when rearranging the equation  `[ok]`
  - gpt-5.6-terra: Makes a sign error when rearranging a linear equation  `[ok]`
- **Wrong mathematical operation/concept**
  - gpt-5.4-mini: Treats the overlap adjustment with the wrong operation  `[ok]`
  - gpt-5.6-luna: Subtracts the overlap when counting mutually exclusive categories  `[ok]`
  - gpt-5.6-terra: Subtracts the overlap instead of adding it when finding the total.  `[ok]`
- **Arithmetical error**
  - gpt-5.4-mini: Makes an arithmetic multiplication error  `[ok]`
  - gpt-5.6-luna: Makes an arithmetic error when multiplying the final factors  `[ok]`
  - gpt-5.6-terra: Makes an arithmetic error when multiplying the final factors.  `[ok]`
- **Unfinished answer**
  - gpt-5.4-mini: Finds only one ratio share instead of the difference between shares  `[ok]`
  - gpt-5.6-luna: Finds a component amount but does not calculate the requested difference  `[ok]`
  - gpt-5.6-terra: Stops after finding one person's share without computing the requested difference.  `[ok]`
- **Wrong mathematical operation/concept**
  - gpt-5.4-mini: Treats work rates as if they were measured in days  `[ok]`
  - gpt-5.6-luna: Confuses total completion time with the corresponding daily work rate  `[ok]`
  - gpt-5.6-terra: Equates combined work rates to elapsed time instead of total work.  `[ok]`

### stepwise

- **Reached correct solution but proceeded further**
  - gpt-5.4-mini: Adds an unnecessary extra step after finding the correct total  `[label_conflict]`
  - gpt-5.6-luna: Rounds a non-integer average down and uses it for every individual amount  `[ok]`
  - gpt-5.6-terra: Continues after finding the total and replaces it with a truncated average.  `[ok]`
- **Missing / Wrong factual knowledge**
  - gpt-5.4-mini: Computes the discounted price using the wrong percent of the original  `[ok]`
  - gpt-5.6-luna: Confuses the discounted price with the discount amount  `[ok]`
  - gpt-5.6-terra: Confuses the remaining sale price with the discount amount.  `[ok]`
- **Extra quantity or Missing quantity**
  - gpt-5.4-mini: Adds an unnecessary extra counting step  `[ok]`
  - gpt-5.6-luna: Double-counts one quantity by applying the number of people twice  `[ok]`
  - gpt-5.6-terra: Double-counts one category when combining equal individual amounts  `[ok]`
- **Misunderstanding of a question**
  - gpt-5.4-mini: Treats the requested number of mistakes as the score itself  `[ok]`
  - gpt-5.6-luna: Subtracts mistakes from the score deficit instead of equating mistakes to it  `[ok]`
  - gpt-5.6-terra: Subtracts the mistakes variable from an already computed score.  `[ok]`
- **Calculation error easily solved by a calculator**
  - gpt-5.4-mini: Applies the equal-proportion division to the wrong total  `[ok]`
  - gpt-5.6-luna: Divides the combined total by types instead of dividing Frank's total  `[ok]`
  - gpt-5.6-terra: Uses the combined total instead of an individual's total when dividing equally.  `[ok]`
- **Unit conversion error**
  - gpt-5.4-mini: Uses the total ratio instead of the corresponding part  `[ok]`
  - gpt-5.6-luna: Divides the given part by the sum of ratio parts instead of its ratio part  `[ok]`
  - gpt-5.6-terra: Divides a known ratio part by the total number of ratio parts  `[ok]`
- **Calculation error easily solved by a calculator**
  - gpt-5.4-mini: Arithmetic mistake in totaling the quantities  `[ok]`
  - gpt-5.6-luna: Makes an arithmetic error when adding the quantities  `[ok]`
  - gpt-5.6-terra: Incorrectly adds the terms in the total.  `[ok]`
- **Missing / Wrong factual knowledge**
  - gpt-5.4-mini: Confuses total tires with number of bicycles  `[ok]`
  - gpt-5.6-luna: Multiplies the number of bicycles instead of the number of tires  `[ok]`
  - gpt-5.6-terra: Treats the multiplier as applying to bicycles instead of total tires  `[ok]`
- **Misunderstanding of a question**
  - gpt-5.4-mini: Subtracts the two fill amounts instead of using the change in buckets  `[ok]`
  - gpt-5.6-luna: Confuses the removed quantity with the remaining quantity used  `[ok]`
  - gpt-5.6-terra: Treats the amount removed as the amount used instead of the amount remaining.  `[ok]`
- **Extra quantity or Missing quantity**
  - gpt-5.4-mini: Counts all walls instead of the remaining wallpaper only  `[ok]`
  - gpt-5.6-luna: Includes a completed part when calculating the remaining total  `[ok]`
  - gpt-5.6-terra: Includes an already completed quantity in the remaining total.  `[ok]`

Counts and flags above are descriptive only. Which description is better is a human judgement; fill in `review_which_is_better` in the CSV.
