# Bring your own candidates and observations

Choose **Use own data** on the overview or in **New research**. Select drugs,
carriers, or general candidates, then describe the research objective and any
required conditions. The interface offers downloadable CSV templates and accepts
either a UTF-8 CSV file or pasted CSV text.

## Candidate list

Use one row per candidate. `candidate_id` is required and unique; `name` is a
readable label. IDs remain text, so `001` and `1` are different candidates.
SMILES, InChIKey, ChEMBL ID and description are optional. Additional columns are
retained as metadata. Measurement evidence belongs in the second table.

```csv
candidate_id,name,description
DEMO-A,Example carrier A,Synthetic example: replace with your own data
DEMO-B,Example carrier B,Synthetic example: replace with your own data
```

For an existing recorded drug library, measurement `candidate_id` values must
match its exact identifiers (the current library uses InChIKeys). Names are not
silently matched to external compounds.

## Measurement table

Use one row per observation, with the candidate ID from the selected library.
Required fields are `candidate_id`, `property`, `value`, and `basis`. Numeric
observations also need a unit; use `1` for dimensionless quantities. Boolean
`true`/`false` or recorded categories may have an empty unit.

```csv
candidate_id,property,value,unit,basis,conditions,source,summary
DEMO-A,particle_size,120,nm,measured,DLS; aqueous dispersion; 25 C,Synthetic example,Illustrative observation
DEMO-B,particle_size,170,nm,measured,DLS; aqueous dispersion; 25 C,Synthetic example,Illustrative observation
```

`basis` is an explicit declaration: `measured`, `curated`, `predicted`,
`simulated`, or `derived`. Specify the experiment, population, dose, duration,
medium, or other relevant context in `conditions`, using plain text or a JSON
object. Different condition sets remain distinct. `source` can identify a DOI,
URL, notebook or dataset. The submitted CSV text, its UTF-8 content hash and CSV
row are retained. The hash identifies the text submitted through file reading or
pasting, after browser decoding and any text normalization. `summary` can supply
the observation in the researcher's own words.

Omit missing observations. Blank numbers, NaN and missing-value markers are
reported as input issues. Zero and `false` are valid observed values.

## Preview and use the data

1. Download a template or choose/paste your CSV.
2. Map file columns to the required fields. The preview shows the first ten rows
   and locates issues by row and field across the complete file.
3. Correct duplicate candidate IDs, unmatched observation IDs, absent units or
   invalid values, then validate again.
4. Save the candidate list, and save its measurement table with that library
   selected. Each saved dataset has an immutable identity; changed data create a
   new version.
5. State what to require and what to prefer in the research objective, then
   start the research. For example: require cell viability of at least 80% under
   the recorded assay conditions, and prefer smaller particle size under the
   selected measurement conditions.

The current import limits are 8 MB, 50,000 data rows and 64 columns per file.
Import validates structure, identities and declared measurement metadata.
Scientific review and qualification follow in the research workflow.

## Scope of the general data workflow

The uploaded-data adapter evaluates exact properties and conditions from the
supplied rows. It works with drug, carrier and general candidate identities.
An optional saved evidence collection can inform criterion development. The
specialized drug adapter remains available for the existing recorded drug
library workflow.

State hard requirements explicitly. A requirement that cannot be bound to a
property, unit and condition set prompts a focused clarification. Required
observations without a preferred direction are recorded as available data.
Predictions remain distinguishable from direct observations. An investigation
with no valid hard condition reports that qualification is not ready.

Examples in this guide and the downloadable templates are synthetic engineering
data, not research findings.
