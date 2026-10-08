# Study configuration

[study_inventory.template.json](study_inventory.template.json) is an unfilled template
for documenting a study before empirical analysis. Null fields are unknowns, not
approved metadata or default scientific assumptions.

Complete a copy in the approved private study environment. Record data ownership,
permissions, sensor characteristics, timestamp conventions, coordinate system, location
error, repeated sessions, bout definitions and validation units. Keep the animal
anonymization key and original coordinates restricted.

The inventory documents the study; it is not the JSON configuration accepted by
`src/run_analysis.py`. For executable configuration fields and examples, see
[the analysis workflow](../docs/ANALYSIS_WORKFLOW.md). Predeclare thresholds, the common
prediction interval and biological blocking before comparing held-out predictions.

See [data governance](../docs/DATA_GOVERNANCE.md) for storage and access guidance.
