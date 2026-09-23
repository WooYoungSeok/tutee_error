# Run comparison — v4__gpt-5.4-mini__dev, v4__gpt-5.6-luna__dev, v4__gpt-5.6-terra__dev, v4__gpt-6-sol__dev, v4__gpt-6-luna__dev

Cases compared: 40

| | gpt-5.4-mini | gpt-5.6-luna | gpt-5.6-terra | gpt-6-sol | gpt-6-luna |
| --- | --- | --- | --- | --- | --- |
| prompt version | v4 | v4 | v4 | v4 | v4 |
| prompt sha256 | 28ef5467bbbac5ce | 28ef5467bbbac5ce | 28ef5467bbbac5ce | 28ef5467bbbac5ce | 28ef5467bbbac5ce |
| model | gpt-5.4-mini | gpt-5.6-luna | gpt-5.6-terra | gpt-6-sol | gpt-6-luna |
| cases with a description | 40 | 36 | 35 | 37 | 36 |
| median description words | 8 | 9 | 9 | 9 | 8 |
| descriptions outside 5-15 words | 2 | 0 | 0 | 1 | 2 |
| shares an uncommon question token | 16 | 12 | 12 | 12 | 10 |
| evidence_quote found verbatim | 34 | 35 | 36 | 40 | 36 |
| processing status | {'ok': 40} | {'ok': 39, 'json_parse_error': 1} | {'ok': 40} | {'ok': 40} | {'ok': 39, 'json_parse_error': 1} |
| model status | {'ok': 38, 'label_conflict': 2} | {'ok': 36, '(none)': 1, 'label_conflict': 3} | {'ok': 35, 'label_conflict': 5} | {'ok': 37, 'label_conflict': 3} | {'ok': 34, '(none)': 1, 'label_conflict': 5} |
| token usage | {'input_tokens': 33388, 'output_tokens': 2168, 'total_tokens': 35556} | {'input_tokens': 33388, 'output_tokens': 8536, 'total_tokens': 41924} | {'input_tokens': 33388, 'output_tokens': 3270, 'total_tokens': 36658} | {'input_tokens': 33388, 'output_tokens': 7148, 'total_tokens': 40536} | {'input_tokens': 33388, 'output_tokens': 10278, 'total_tokens': 43666} |

## Cases where the status differs between runs (8)

| dataset | sample_id | label | gpt-5.4-mini | gpt-5.6-luna | gpt-5.6-terra | gpt-6-sol | gpt-6-luna |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mathclean | mathclean:021b0bf3e810c899 | computing error | ok | ok | label_conflict | ok | ok |
| mathclean | mathclean:49d0c9b1827cc310 | logic error | ok | None | ok | ok | None |
| mathclean | mathclean:6c8605b2eb64ed2b | expression error | ok | label_conflict | label_conflict | label_conflict | label_conflict |
| mathclean | mathclean:8351714360a1cde0 | expression error | ok | label_conflict | label_conflict | label_conflict | label_conflict |
| mathclean | mathclean:9ac6eb03c135487d | logic error | ok | ok | label_conflict | ok | ok |
| stepwise | stepwise:231586f8d27166cb | Reached correct solution but proceeded further | label_conflict | ok | ok | ok | ok |
| stepwise | stepwise:a4cfc51315961b61 | Calculation error easily solved by a calculator | ok | ok | ok | ok | label_conflict |
| stepwise | stepwise:aa3c4787242df63d | Unit conversion error | ok | ok | ok | ok | label_conflict |

## Descriptions side by side

### eic

- **referencing_context_value_error**
  - gpt-5.4-mini: Uses an incorrect value for the seed cost  `[ok]`
  - gpt-5.6-luna: Uses an incorrect cost value when calculating total expenses  `[ok]`
  - gpt-5.6-terra: Uses an incorrect value from the given information.  `[ok]`
  - gpt-6-sol: Uses an incorrect given cost when calculating total expenses  `[ok]`
  - gpt-6-luna: Misreads a stated cost value  `[ok]`
- **unit_conversion_error**
  - gpt-5.4-mini: Converts time units incorrectly  `[ok]`
  - gpt-5.6-luna: Uses an incorrect conversion between hours and minutes  `[ok]`
  - gpt-5.6-terra: Uses an incorrect conversion between hours and minutes.  `[ok]`
  - gpt-6-sol: Uses an incorrect conversion between hours and minutes  `[ok]`
  - gpt-6-luna: Uses an incorrect conversion between hours and minutes  `[ok]`
- **operator_error**
  - gpt-5.4-mini: Uses an invalid operation instead of taking a percent decrease  `[ok]`
  - gpt-5.6-luna: Converts a percentage incorrectly by multiplying by 100 instead of dividing by 100  `[ok]`
  - gpt-5.6-terra: Multiplies by the percentage number instead of converting it to a decimal.  `[ok]`
  - gpt-6-sol: Multiplies by 100 instead of dividing by 100 to calculate a percent  `[ok]`
  - gpt-6-luna: Treats a percentage as a whole-number multiplier  `[ok]`
- **calculation_error**
  - gpt-5.4-mini: Adds the difference instead of the total  `[ok]`
  - gpt-5.6-luna: Makes an arithmetic addition error  `[ok]`
  - gpt-5.6-terra: Makes an arithmetic error when adding quantities.  `[ok]`
  - gpt-6-sol: Miscomputes a sum  `[ok]`
  - gpt-6-luna: Makes an addition error  `[ok]`
- **missing_step**
  - gpt-5.4-mini: Uses the original total instead of the remainder for the second part  `[ok]`
  - gpt-5.6-luna: Takes a fraction of the original total instead of the remainder  `[ok]`
  - gpt-5.6-terra: Calculates a fraction of the original amount instead of the remainder  `[ok]`
  - gpt-6-sol: Calculates a fraction of the original total instead of the remainder  `[ok]`
  - gpt-6-luna: Applies a fraction to the original amount instead of the remainder  `[ok]`
- **adding_irrelevant_information**
  - gpt-5.4-mini: Adds an irrelevant expense not in the problem  `[ok]`
  - gpt-5.6-luna: Adds an unprovided expense to the profit calculation  `[ok]`
  - gpt-5.6-terra: Introduces an unsupported expense into the profit calculation  `[ok]`
  - gpt-6-sol: Subtracts an expense not given in the problem  `[ok]`
  - gpt-6-luna: Adds an unsupported expense to the calculation  `[ok]`
- **adding_irrelevant_information**
  - gpt-5.4-mini: Adds an unsupported extra bonus amount  `[ok]`
  - gpt-5.6-luna: Adds an unsupported bonus to the total earnings  `[ok]`
  - gpt-5.6-terra: Adds an unsupported bonus payment to the calculation  `[ok]`
  - gpt-6-sol: Adds an unsupported bonus to the total.  `[ok]`
  - gpt-6-luna: Adds an unsupported quantity to a calculation  `[ok]`
- **counting_error**
  - gpt-5.4-mini: Uses the wrong number of days in the total  `[ok]`
  - gpt-5.6-luna: Counts the days from Monday to Saturday incorrectly  `[ok]`
  - gpt-5.6-terra: Uses the wrong number of days when finding a weekly total.  `[ok]`
  - gpt-6-sol: Undercounts the days in an inclusive weekday range  `[ok]`
  - gpt-6-luna: Miscounts the number of days in an inclusive interval  `[ok]`
- **confusing_formula_error**
  - gpt-5.4-mini: Uses perimeter-like addition instead of area multiplication  `[ok]`
  - gpt-5.6-luna: Uses perimeter addition instead of multiplying length by width  `[ok]`
  - gpt-5.6-terra: Uses the perimeter formula instead of the area formula  `[ok]`
  - gpt-6-sol: Uses the perimeter formula instead of the area formula.  `[ok]`
  - gpt-6-luna: Uses the perimeter formula instead of the area formula  `[ok]`
- **referencing_previous_step_value_error**
  - gpt-5.4-mini: Uses an incorrect value from a previous step  `[ok]`
  - gpt-5.6-luna: Uses an incorrect value from a previous calculation  `[ok]`
  - gpt-5.6-terra: Uses a value not obtained in the previous calculation.  `[ok]`
  - gpt-6-sol: Uses a different value instead of the quantity calculated earlier.  `[ok]`
  - gpt-6-luna: Uses an incorrect prior-step value in a subsequent calculation  `[ok]`

### mathclean

- **computing error**
  - gpt-5.4-mini: Applies the weekly raise multiplicatively each week to the daily rate, rather than increasing from the current week’s earnings correctly  `[ok]`
  - gpt-5.6-luna: Reports an arithmetic result inconsistent with the implemented calculation  `[ok]`
  - gpt-5.6-terra: None  `[label_conflict]`
  - gpt-6-sol: Reports a numerical result inconsistent with the calculation shown  `[ok]`
  - gpt-6-luna: Reports a total inconsistent with the calculations shown  `[ok]`
- **logic error**
  - gpt-5.4-mini: Adds angles that should be related by a linear pair  `[ok]`
  - gpt-5.6-luna: None  `[None]`
  - gpt-5.6-terra: Misidentifies the angle relationship and equates an angle to a sum.  `[ok]`
  - gpt-6-sol: Treats an angle supplementary to a sum as equal to that sum  `[ok]`
  - gpt-6-luna: None  `[None]`
- **computing error**
  - gpt-5.4-mini: Computes the arithmetic progression sum incorrectly  `[ok]`
  - gpt-5.6-luna: Confuses the final term of an arithmetic sequence with its cumulative total  `[ok]`
  - gpt-5.6-terra: Confuses the final weekly amount with the total accumulated amount.  `[ok]`
  - gpt-6-sol: Confuses a term in an arithmetic sequence with its cumulative sum  `[ok]`
  - gpt-6-luna: Uses one week's savings amount instead of summing weekly savings.  `[ok]`
- **computing error**
  - gpt-5.4-mini: Uses a fractional result instead of a whole number count  `[label_conflict]`
  - gpt-5.6-luna: None  `[label_conflict]`
  - gpt-5.6-terra: None  `[label_conflict]`
  - gpt-6-sol: None  `[label_conflict]`
  - gpt-6-luna: None  `[label_conflict]`
- **computing error**
  - gpt-5.4-mini: Treats increased side lengths as if all diagonals increased too  `[ok]`
  - gpt-5.6-luna: Applies only one monthly increase instead of accumulating all monthly increases  `[ok]`
  - gpt-5.6-terra: Omits several classes of diagonals from the total sum  `[ok]`
  - gpt-6-sol: Adds only one increment after multiple periods of increase  `[ok]`
  - gpt-6-luna: Does not accumulate repeated monthly increases  `[ok]`
- **expression error**
  - gpt-5.4-mini: Substitutes the wrong coordinate into the parametric equations  `[ok]`
  - gpt-5.6-luna: None  `[label_conflict]`
  - gpt-5.6-terra: None  `[label_conflict]`
  - gpt-6-sol: None  `[label_conflict]`
  - gpt-6-luna: None  `[label_conflict]`
- **logic error**
  - gpt-5.4-mini: Computes the new common factor after scaling incorrectly  `[ok]`
  - gpt-5.6-luna: Omits larger common factors when identifying the greatest common factor  `[ok]`
  - gpt-5.6-terra: Omits shared factors and identifies a non-greatest common factor.  `[ok]`
  - gpt-6-sol: Selects a common factor that is not the greatest  `[ok]`
  - gpt-6-luna: Overlooks common factors when determining the greatest common factor  `[ok]`
- **expression error**
  - gpt-5.4-mini: Adds the repeated climbs instead of using the ladder length once per worker  `[ok]`
  - gpt-5.6-luna: None  `[label_conflict]`
  - gpt-5.6-terra: None  `[label_conflict]`
  - gpt-6-sol: None  `[label_conflict]`
  - gpt-6-luna: None  `[label_conflict]`
- **logic error**
  - gpt-5.4-mini: Treats each grave type separately instead of continuing the decreasing times across all graves  `[ok]`
  - gpt-5.6-luna: Calculates the final sum incorrectly  `[ok]`
  - gpt-5.6-terra: None  `[label_conflict]`
  - gpt-6-sol: Misadds the individual times when calculating the total  `[ok]`
  - gpt-6-luna: Makes an arithmetic error when summing the individual times  `[ok]`
- **expression error**
  - gpt-5.4-mini: Uses the wrong quantity in the final multiplication  `[ok]`
  - gpt-5.6-luna: Omits the repeated frequency when calculating the weekly total  `[ok]`
  - gpt-5.6-terra: Introduces an unsupported annual conversion instead of using the weekly quantity.  `[ok]`
  - gpt-6-sol: Omits a frequency factor when calculating a weekly total  `[ok]`
  - gpt-6-luna: Omits a frequency factor when calculating a repeated total  `[ok]`

### mathedu

- **Comprehension error**
  - gpt-5.4-mini: Uses a simple-interest formula incorrectly by treating the rate-time product as a decimal factor  `[ok]`
  - gpt-5.6-luna: Converts a mixed number to the wrong improper fraction  `[ok]`
  - gpt-5.6-terra: Converts a mixed number to an improper fraction incorrectly.  `[ok]`
  - gpt-6-sol: Treats a mixed number as an improper fraction by joining its digits  `[ok]`
  - gpt-6-luna: Converts a mixed number to an improper fraction incorrectly  `[ok]`
- **Comprehension error**
  - gpt-5.4-mini: Sets up the age relationship backward  `[ok]`
  - gpt-5.6-luna: Reports a related quantity instead of the requested quantity  `[ok]`
  - gpt-5.6-terra: Equates age relationships without defining all variables consistently.  `[ok]`
  - gpt-6-sol: Reports a different quantity instead of the one asked for  `[ok]`
  - gpt-6-luna: Reports a related quantity instead of the requested variable  `[ok]`
- **Measurement error**
  - gpt-5.4-mini: Uses inconsistent units in a measurement calculation  `[ok]`
  - gpt-5.6-luna: Fails to convert measurements to consistent units before calculating area  `[ok]`
  - gpt-5.6-terra: Divides areas expressed in incompatible measurement units.  `[ok]`
  - gpt-6-sol: Divides areas measured in different units without converting them first  `[ok]`
  - gpt-6-luna: Fails to convert units before comparing areas  `[ok]`
- **Careless error**
  - gpt-5.4-mini: Uses the area to infer side lengths incorrectly  `[ok]`
  - gpt-5.6-luna: Changes a given measurement during the final addition  `[ok]`
  - gpt-5.6-terra: Uses an incorrect side length when adding the fenced sides.  `[ok]`
  - gpt-6-sol: Uses an incorrect side length when adding the fenced sides  `[ok]`
  - gpt-6-luna: Uses an incorrect side length in the perimeter calculation  `[ok]`
- **Lack of necessary mathematical concepts**
  - gpt-5.4-mini: Subtracts the discount from present worth instead of using the proper discount relation  `[ok]`
  - gpt-5.6-luna: Subtracts true discount from present worth instead of calculating banker’s discount  `[ok]`
  - gpt-5.6-terra: Subtracts the discount from present worth instead of finding banker's discount.  `[ok]`
  - gpt-6-sol: Subtracts true discount from present value to find banker’s discount  `[ok]`
  - gpt-6-luna: Uses subtraction instead of the relationship between true and banker’s discounts  `[ok]`
- **Algebraic error**
  - gpt-5.4-mini: Fails to isolate the variable correctly after setting up the slope equation  `[ok]`
  - gpt-5.6-luna: Makes a sign error when rearranging the equation  `[ok]`
  - gpt-5.6-terra: Makes a sign error when rearranging a linear equation  `[ok]`
  - gpt-6-sol: Loses a negative sign when combining like terms  `[ok]`
  - gpt-6-luna: Makes a sign error when rearranging an equation  `[ok]`
- **Wrong mathematical operation/concept**
  - gpt-5.4-mini: Treats the overlap adjustment with the wrong operation  `[ok]`
  - gpt-5.6-luna: Subtracts the overlap when counting mutually exclusive categories  `[ok]`
  - gpt-5.6-terra: Subtracts the overlap instead of adding it when finding the total.  `[ok]`
  - gpt-6-sol: Subtracts the intersection when adding categories that already exclude it.  `[ok]`
  - gpt-6-luna: Subtracts the overlap instead of adding all disjoint categories  `[ok]`
- **Arithmetical error**
  - gpt-5.4-mini: Makes an arithmetic multiplication error  `[ok]`
  - gpt-5.6-luna: Makes an arithmetic error when multiplying the final factors  `[ok]`
  - gpt-5.6-terra: Makes an arithmetic error when multiplying the final factors.  `[ok]`
  - gpt-6-sol: Drops a zero when multiplying whole numbers  `[ok]`
  - gpt-6-luna: Makes an arithmetic error when multiplying  `[ok]`
- **Unfinished answer**
  - gpt-5.4-mini: Finds only one ratio share instead of the difference between shares  `[ok]`
  - gpt-5.6-luna: Finds a component amount but does not calculate the requested difference  `[ok]`
  - gpt-5.6-terra: Stops after finding one person's share without computing the requested difference.  `[ok]`
  - gpt-6-sol: Finds the largest share but does not subtract the smallest share.  `[ok]`
  - gpt-6-luna: Finds one part instead of the difference between two parts  `[ok]`
- **Wrong mathematical operation/concept**
  - gpt-5.4-mini: Treats work rates as if they were measured in days  `[ok]`
  - gpt-5.6-luna: Confuses total completion time with the corresponding daily work rate  `[ok]`
  - gpt-5.6-terra: Equates combined work rates to elapsed time instead of total work.  `[ok]`
  - gpt-6-sol: Uses completion time instead of its reciprocal as the combined work rate  `[ok]`
  - gpt-6-luna: Confuses elapsed time with completed work when setting up a work-rate equation  `[ok]`

### stepwise

- **Reached correct solution but proceeded further**
  - gpt-5.4-mini: Adds an unnecessary extra step after finding the correct total  `[label_conflict]`
  - gpt-5.6-luna: Rounds a non-integer average down and uses it for every individual amount  `[ok]`
  - gpt-5.6-terra: Continues after finding the total and replaces it with a truncated average.  `[ok]`
  - gpt-6-sol: Rounds an average to a whole-number individual amount and changes the total.  `[ok]`
  - gpt-6-luna: Treats a rounded average as each individual’s contribution  `[ok]`
- **Missing / Wrong factual knowledge**
  - gpt-5.4-mini: Computes the discounted price using the wrong percent of the original  `[ok]`
  - gpt-5.6-luna: Confuses the discounted price with the discount amount  `[ok]`
  - gpt-5.6-terra: Confuses the remaining sale price with the discount amount.  `[ok]`
  - gpt-6-sol: Confuses the remaining percentage of a price with the discount percentage  `[ok]`
  - gpt-6-luna: Confuses the discounted price percentage with the discount amount  `[ok]`
- **Extra quantity or Missing quantity**
  - gpt-5.4-mini: Adds an unnecessary extra counting step  `[ok]`
  - gpt-5.6-luna: Double-counts one quantity by applying the number of people twice  `[ok]`
  - gpt-5.6-terra: Double-counts one category when combining equal individual amounts  `[ok]`
  - gpt-6-sol: Double-counts a quantity by multiplying an already combined total again  `[ok]`
  - gpt-6-luna: Double-counts a quantity when calculating the combined total  `[ok]`
- **Misunderstanding of a question**
  - gpt-5.4-mini: Treats the requested number of mistakes as the score itself  `[ok]`
  - gpt-5.6-luna: Subtracts mistakes from the score deficit instead of equating mistakes to it  `[ok]`
  - gpt-5.6-terra: Subtracts the mistakes variable from an already computed score.  `[ok]`
  - gpt-6-sol: Subtracts the mistake count from the score shortfall instead of equating them  `[ok]`
  - gpt-6-luna: Confuses points earned with points lost when calculating mistakes  `[ok]`
- **Calculation error easily solved by a calculator**
  - gpt-5.4-mini: Applies the equal-proportion division to the wrong total  `[ok]`
  - gpt-5.6-luna: Divides the combined total by types instead of dividing Frank's total  `[ok]`
  - gpt-5.6-terra: Uses the combined total instead of an individual's total when dividing equally.  `[ok]`
  - gpt-6-sol: Multiplies the overall per-type count to find one person's per-type count  `[ok]`
  - gpt-6-luna: Confuses combined per-type totals with one person's per-type share  `[label_conflict]`
- **Unit conversion error**
  - gpt-5.4-mini: Uses the total ratio instead of the corresponding part  `[ok]`
  - gpt-5.6-luna: Divides the given part by the sum of ratio parts instead of its ratio part  `[ok]`
  - gpt-5.6-terra: Divides a known ratio part by the total number of ratio parts  `[ok]`
  - gpt-6-sol: Divides a part by the total of the ratio parts to find the scale factor  `[ok]`
  - gpt-6-luna: Uses total ratio parts instead of the corresponding part to scale.  `[label_conflict]`
- **Calculation error easily solved by a calculator**
  - gpt-5.4-mini: Arithmetic mistake in totaling the quantities  `[ok]`
  - gpt-5.6-luna: Makes an arithmetic error when adding the quantities  `[ok]`
  - gpt-5.6-terra: Incorrectly adds the terms in the total.  `[ok]`
  - gpt-6-sol: Adds the terms in a sum incorrectly  `[ok]`
  - gpt-6-luna: Makes an arithmetic error when summing quantities  `[ok]`
- **Missing / Wrong factual knowledge**
  - gpt-5.4-mini: Confuses total tires with number of bicycles  `[ok]`
  - gpt-5.6-luna: Multiplies the number of bicycles instead of the number of tires  `[ok]`
  - gpt-5.6-terra: Treats the multiplier as applying to bicycles instead of total tires  `[ok]`
  - gpt-6-sol: Multiplies the number of bicycles instead of their total tires  `[ok]`
  - gpt-6-luna: Applies a multiplier to the number of objects instead of their countable parts  `[ok]`
- **Misunderstanding of a question**
  - gpt-5.4-mini: Subtracts the two fill amounts instead of using the change in buckets  `[ok]`
  - gpt-5.6-luna: Confuses the removed quantity with the remaining quantity used  `[ok]`
  - gpt-5.6-terra: Treats the amount removed as the amount used instead of the amount remaining.  `[ok]`
  - gpt-6-sol: Confuses the amount removed with the amount remaining.  `[ok]`
  - gpt-6-luna: Confuses a removed quantity with the remaining quantity  `[ok]`
- **Extra quantity or Missing quantity**
  - gpt-5.4-mini: Counts all walls instead of the remaining wallpaper only  `[ok]`
  - gpt-5.6-luna: Includes a completed part when calculating the remaining total  `[ok]`
  - gpt-5.6-terra: Includes an already completed quantity in the remaining total.  `[ok]`
  - gpt-6-sol: Counts already completed work as part of the remaining work.  `[ok]`
  - gpt-6-luna: Counts completed work again when calculating what remains  `[ok]`

Counts and flags above are descriptive only. Which description is better is a human judgement; fill in `review_which_is_better` in the CSV.
