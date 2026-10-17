# Bring your own candidates and observations

[中文](zh/csv-input.md) · [Install and start MAS](installation.md)

Open **Use own data** from the overview or **New research**, choose **Drug**, **Carrier** or **General**, and import a candidate list followed by its observations. The interface accepts a UTF-8 CSV file or pasted CSV text and offers downloadable templates. Start the workbench with local operations enabled as described in the installation guide.

The two CSV examples below contain **synthetic, illustrative data only**. Their names, values and conditions are invented to explain the format; replace them with your own candidates and recorded observations. The [repository templates](../config/examples/) contain headers only and need at least one data row before import.

## Candidate list

Use one row per candidate. Map your CSV columns to these fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `candidate_id` | Yes | Unique text identifier, at most 200 characters. |
| `name` | No | Display label; the ID is used when empty. |
| `smiles` | No | Declared SMILES identifier, when applicable. |
| `inchikey` | No | Declared InChIKey identifier, when applicable. |
| `chembl_id` | No | Declared ChEMBL identifier, when applicable. |
| `description` | No | Description of the candidate. |

Additional candidate columns are retained as metadata. Supply measurement evidence in the separate observation table. Candidate IDs remain text: `001` and `1` identify different candidates. When preparing a file in a spreadsheet, format the identifier column as text before entering or exporting IDs so leading zeros survive.

Illustrative `candidates.csv`:

```csv
candidate_id,name,description
DEMO-A,Example carrier A,Synthetic format example
DEMO-B,Example carrier B,Synthetic format example
```

Save this candidate list before importing its measurements. For an existing recorded drug library, observation IDs must match the library's exact identifiers, which may be InChIKeys. The importer does not match compound names to external identities automatically. Optional structure identifiers are preserved as supplied; CSV import does not verify chemical identity.

## Measurement table

Use one row per observation. A candidate can have several properties, repeats or condition sets.

| Field | Required | Meaning |
| --- | --- | --- |
| `candidate_id` | Yes | Exact ID from the candidate library selected for this upload. |
| `property` | Yes | Recorded property or endpoint, such as `particle_size`. |
| `value` | Yes | A finite number, `true`/`false`, or a recorded category. |
| `basis` | Yes | One of `measured`, `curated`, `predicted`, `simulated`, `derived`. The importer does not guess the basis. |
| `unit` | For numeric values | Recorded unit; use `1` for a dimensionless quantity. Boolean and category values can have an empty unit. |
| `conditions` | No | Experimental context as plain text or a JSON object. |
| `source` | No | DOI, URL, notebook, dataset or other source reference. |
| `summary` | No | Observation stated in the researcher's own words. |

Illustrative `measurements.csv`, linked to the synthetic candidates above:

```csv
candidate_id,property,value,unit,basis,conditions,source,summary
DEMO-A,particle_size,120,nm,measured,DLS; aqueous dispersion; 25 C,Synthetic format example,Illustrative observation only
DEMO-B,particle_size,170,nm,measured,DLS; aqueous dispersion; 25 C,Synthetic format example,Illustrative observation only
```

Record the actual assay, population, dose, duration, medium, temperature and other relevant conditions. Different condition sets remain distinct in research evaluation. A JSON condition must be a valid object; quote and escape it according to CSV rules if it contains commas or quotation marks. Plain text is sufficient when you do not need structured fields.

`conditions` and `source` are optional for import, but provide them whenever known so the observation has a traceable scope. Missing conditions produce a warning and remain unspecified. When `source` is empty, the saved observation uses the upload filename as its declared source and retains the absence of an explicit source in provenance. The submitted text, its UTF-8 content hash, filename and CSV row are preserved. The hash describes text submitted after browser decoding and any text normalization.

Omit missing observations. Blank required values, NaN, nonfinite numbers and missing-value labels such as `NA`, `unknown` or `missing` are input errors. Zero and `false` are valid observed values. Preserve the actual evidence basis; a model estimate should retain its predicted or simulated status.

## Preview, correct and save

1. Choose or paste the candidate CSV, review its column mapping, and validate it. Common aliases such as `sample_id` for `candidate_id`, `endpoint` for `property`, and `result` for `value` can be detected automatically; inspect the mapping before saving.
2. Correct any reported issues and validate again. Each CSV column can map to at most one import field. Save the candidate list when the preview is valid.
3. Select that saved candidate library and import its measurement CSV. Review the mapping, units, basis and experimental conditions, then save it.
4. Select the saved data in **New research**. Describe the objective, required observations, hard conditions and preferences, then start the research workflow under its configured budget.

The preview shows the first ten data rows while validating the full file. Row errors identify the CSV row and field; at most 200 detailed errors are displayed, alongside the total error count. Structural errors can prevent a preview from opening. Saving is blocked until all errors are resolved; warnings explain accepted data with limitations.

| Reported problem | Correction |
| --- | --- |
| Required field has no mapped column | Map it to the appropriate column, or add the column and reload the file. |
| Duplicate candidate ID | Keep one candidate row per ID; put repeated observations in the measurement table. |
| Observation ID absent from selected library | Select the correct library or correct the ID in the source CSV. |
| Numeric observation lacks a unit | Supply its recorded unit, or `1` for a dimensionless quantity. |
| Invalid basis, missing value or nonfinite number | Supply the actual supported basis/value, or omit a missing observation. |
| Invalid JSON conditions | Correct the JSON object or use plain text. |
| Broken CSV, uneven field counts or encoding issue | Export as UTF-8 CSV and quote fields containing commas, quotation marks or line breaks. |

Headers must be distinct and nonempty. A UTF-8 byte order mark is accepted. Current limits are **8 MB of UTF-8 text, 50,000 data rows and 64 columns per file**. Header-only or empty files are rejected. Split files exceeding these limits before import.

Each saved dataset has an immutable identity. Repeating the same upload and mapping returns that saved version; changing the file or mapping creates another version. Reimport corrections through the interface so the original submission remains traceable.

## Use the observations in research

The uploaded-data adapter evaluates properties, units and conditions from the supplied records for drug, carrier and general candidates. An optional saved evidence collection can inform criterion development. The specialized drug adapter also supports recorded compound libraries and external evidence tools.

State hard conditions explicitly and identify their properties, units and scope. If a required condition cannot be bound to the supplied data, the workflow asks for the essential clarification. Required observations without a preferred direction are treated as available data. Predictions remain distinguishable from direct observations. An investigation with no valid hard condition reports that qualification is not ready.

Import validates file structure, IDs and declared observation metadata. Scientific review, criterion development and qualification occur in the research workflow. The synthetic examples above are format demonstrations and have not been scientifically evaluated.
