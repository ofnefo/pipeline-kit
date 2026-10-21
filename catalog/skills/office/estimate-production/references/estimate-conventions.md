# Estimate conventions (configurable defaults)

Practical defaults for event and project estimates in the Russian market. Each project may override them; record
overrides in the project config.

## Prices

- Use real current market prices. A value taken from a market benchmark rather than a quote is labelled as such.
- Work order: equipment first, then decor/branding, then the full estimate by ТЗ sections.
- When the operator asks for a rough estimate "by our volume", produce it and label it as calculated.

## Two files

| File | Content |
|---|---|
| Internal calculation | summary, parameters, price reference, blocks, cost, assumptions |
| Client file | blocks only; markup baked into unit prices; no markup line, no internal notes or assumptions |

- Default markup about 30-40% (e.g. ~35% equipment, ~40% decor) unless a target sum is given. Reach a target through
  markup and honest lines, never by inflating quantities.
- Agency markup is a separate editable parameter at the end of the internal file. It is not added in 44-ФЗ tender
  calculations.

## Tender parameters sheet (editable cells)

- НМЦК (including VAT), the winner's discount share, ceiling = НМЦК × (1 − share).
- Taxes according to the project's regime, credit rate × term, build-up days and event days.
- The summary shows the ceiling, the margin to the ceiling, and profit and profitability measured from the ceiling.
- Each line keeps forecast (tender estimate), actual and remainder.

## VAT wording

Prepare wording for 20%, 5%, 7%, УСН, self-employed and "без НДС" cases. Check the current rates and wording against
the Tax Code (ст. 164 НК РФ) before use; never guess an unresolved regime.

## Savings and options

Savings go on a separate levers sheet with a 1/0 switch per lever until the decision-maker picks them; the main
estimate does not silently include them.

## Line conventions

- Venue: include mandatory services (security, cleaning) even if the venue itself is free.
- Meals according to the ТЗ; breakfasts included in lodging appear at price 0 with a comment.
- Decor reserve +20-30%.
- Contractor accreditation as separate lines.
- Record the payer of every payment; cash is a separate block.
- Closing documents from each contractor: contract, act and УПД.
- Cargo insurance: premium = insured sum × rate. Typical rates: about 0.2-0.5% for an event period, 1-2% for annual
  all-risks cover. Keep rate and limit as editable cells.
