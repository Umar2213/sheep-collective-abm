# Empirical sheep workstream

## Position within ARC Discovery Project DP260101231

ARC project: **How individual variation drives collective motion**

This repository supports the sheep component of the broader project. The specific role of this workstream is the **empirical side of the sheep component that feeds into the modelling**.

The broader ARC project links biological experiments, data science and mathematical biology to understand how individual variation affects collective motion. The sheep system is especially important because individuals recognise one another and form social relationships.

## Scope of this workstream

The empirical sheep workstream should produce clean, auditable and biologically interpretable data products that the modelling team can use without needing to reconstruct the entire empirical pipeline.

Primary responsibilities:

1. Curate and document sheep movement and associated metadata.
2. Establish reproducible quality control and preprocessing.
3. Quantify individual movement variation and its repeatability.
4. Estimate social relationships using leakage-safe observation periods.
5. Define movement bouts and biologically meaningful analysis units.
6. Test whether individual and dyadic information improves held-out prediction.
7. Export clearly specified empirical summaries, networks and fitted quantities to the modelling workstream.
8. Keep restricted raw data and precise farm information outside the public GitHub repository.

This workstream should not assume that every model parameter has a direct biological interpretation. Parameter recovery, out-of-sample prediction and independent social-network estimation are required before strong interpretation.

## Core empirical questions

1. Are there persistent individual differences in movement responsiveness or movement tendency?
2. Are sheep social relationships sufficiently stable to be estimated independently of the movement bouts being predicted?
3. Do individual differences improve prediction beyond a homogeneous baseline?
4. Do independently estimated dyadic relationships improve prediction beyond geometry or proximity alone?
5. Do individual responsiveness and social relationships provide non-redundant predictive information?
6. Which empirical quantities are sufficiently identifiable and stable to pass to the mathematical modelling team?

## Work packages

### WP0. Data governance and study inventory

Create a study inventory before analysis.

Record:

- dataset owner and access conditions
- animal ethics or animal-use approval references
- collection dates and study locations at the permitted level of detail
- sensor type and sampling rate
- coordinate reference system
- animal and group composition
- behavioural or physiological covariates
- missing-data patterns
- restrictions on publication or sharing

Deliverables:

- data dictionary
- provenance record
- raw-data checksum manifest
- access and publication rules

### WP1. Raw trajectory audit

Use immutable raw files. Never edit raw files in place.

Required checks include:

- required identifiers are present
- timestamps parse correctly
- coordinate values are finite
- duplicate keys are absent
- sampling intervals are quantified
- track gaps are reported
- coordinate units are documented
- projected metric coordinates are used for metric interaction distances

The existing `src/trajectory_validation.py` and `docs/TRAJECTORY_DATA_SPEC.md` provide the repository standard.

### WP2. Reproducible preprocessing

Build a scripted pipeline from raw trajectories to analysis-ready trajectories.

Record every decision involving:

- coordinate projection
- clock correction or time alignment
- filtering of poor fixes
- interpolation
- smoothing
- resampling
- minimum movement threshold
- heading calculation
- speed calculation
- bout definition

Do not silently repair tracks.

### WP3. Movement bouts and behavioural states

Define independent or approximately independent biological blocks before model comparison.

Candidate blocks include:

- complete movement bouts
- observation sessions
- days
- flocks or social groups

Avoid random train/test splitting of adjacent GPS frames.

If stop/start states or grazing versus directed travel are important, define these states with a method that is independent of the model comparison wherever possible.

### WP4. Individual variation

Estimate descriptive and repeatability measures before interpreting model parameters.

Candidate empirical traits include:

- mean and variance of speed
- turning tendency
- movement persistence
- response to neighbour configuration
- position within the group
- initiation and following tendency
- state transition rates

Where repeated measurements exist, quantify within-individual and among-individual variance.

### WP5. Social relationships

Estimate dyadic social relationships from data that are independent of the held-out movement bout whenever possible.

Potential sources include:

- association outside focal movement bouts
- resting or grazing proximity
- repeated nearest-neighbour structure
- independent behavioural observations

Required controls:

- uniform-neighbour model
- proximity-only model
- shuffled social ties
- network-preserving shuffles where justified

Do not build the test network from the same trajectory segment that it is later used to predict.

### WP6. Empirical model comparison

Use the nested model hierarchy already defined in the repository:

| Model | Individual responsiveness | Dyadic ties | Outgoing influence |
|---|---|---|---|
| M0 | common | uniform | fixed 1 |
| M1 | individual | uniform | fixed 1 |
| M2 | common | independently measured or training-only | fixed 1 |
| M3 | individual | independently measured or training-only | fixed 1 |
| M4 | individual | measured or estimated | estimate only if identifiable |

Primary empirical comparison should focus on M0 to M3.

M4 should only be used if synthetic recovery demonstrates that outgoing influence can be separated from dyadic weighting.

Evaluate on complete held-out biological blocks.

### WP7. Modelling handoff

The modelling team should receive versioned empirical products, not undocumented spreadsheets.

Recommended handoff products:

- cleaned trajectory table
- frozen train/test fold table
- social-network matrix with method and observation period
- individual-level empirical summary table
- group and bout metadata
- observation-error summary
- parameter-recovery report
- model-comparison metrics
- uncertainty summaries
- machine-readable metadata
- checksum manifest
- README describing exactly how each product was generated

Each handoff should include a version identifier and Git commit SHA for the code that generated it.

## Minimum data schema

Required movement columns:

- `group_id`
- `bout_id`
- `individual_id`
- `timestamp`
- `x`
- `y`

Recommended additional columns depend on the actual study and may include:

- `date`
- `fix_quality`
- `speed`
- `heading`
- `behavioural_state`
- `environment_id`
- `pasture_id`
- `sex`
- `age_class`
- justified physiological or behavioural covariates

Use anonymized animal identifiers in analysis products.

## Decision gates

### Data gate

Raw data provenance, units, coordinate system, sampling design and restrictions are documented.

### Quality gate

Trajectory integrity checks pass or exclusions are explicitly reported.

### Independence gate

Training and test blocks are biologically defensible and no test information enters preprocessing, social-network estimation or model fitting.

### Identifiability gate

Synthetic recovery identifies which latent quantities can be estimated reliably.

### Prediction gate

More complex models are judged by held-out predictive performance and block-level uncertainty, not in-sample fit alone.

### Interpretation gate

Biological interpretation is limited to quantities supported by recovery, stability and independent empirical evidence.

### Handoff gate

Every modelling input is versioned, documented and reproducible from permitted source data.

## Public repository versus restricted server

The public GitHub repository should contain:

- source code
- tests
- synthetic or explicitly releasable example data
- data schemas
- documentation
- derived summary results that are approved for release

The public GitHub repository should not contain:

- restricted raw sheep trajectories
- precise farm coordinates
- owner or participant identifying information
- credentials
- private server paths containing sensitive identifiers
- unpublished restricted datasets

Large or restricted data should remain on the approved research server and be referenced through anonymized manifests and checksums.

## References

- ARC grant record: https://dataportal.arc.gov.au/RGS/Web/Grants/DP260101231
- Repository research plan: `docs/RESEARCH_PLAN.md`
- Trajectory specification: `docs/TRAJECTORY_DATA_SPEC.md`
- Analysis workflow: `docs/ANALYSIS_WORKFLOW.md`
- Model specification: `docs/MODEL.md`
