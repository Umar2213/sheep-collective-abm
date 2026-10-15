# Public-data demonstration: 14 Merino sheep

This example runs the repository's analysis on published, openly licensed tracking data,
so the pipeline and the website can be demonstrated and checked without project data.

## Source and licence

Jadhav V, Pasqua R, Zanon C, et al. (2024). Collective responses of flocking sheep
(*Ovis aries*) to a herding dog (border collie). *Communications Biology* 7:1543.
doi:10.1038/s42003-024-07245-8. Raw positions: `main_text/sheepR.dat` in
github.com/tee-lab/collective-responses-of-flocking-sheep-to-herding-dog (commit 2c02a88),
archived at doi:10.5281/zenodo.13982895 (CC BY 4.0). Derived CSV files are not committed here;
rebuild them with the script below and cite the source whenever you show them.

## Files

| File | Purpose |
|---|---|
| `PROTOCOL.md` | Every setting, fixed in writing before any model was fitted, plus recorded additions |
| `prepare_sheep_data.py` | Builds `trajectories.csv`, `ties.csv`, `config.json` and `provenance.json` from the source file |
| `EXPECTED_FINGERPRINTS.txt` | SHA-256 of the prepared inputs and of all 19 reference outputs |

## Run it

```bash
git clone https://github.com/tee-lab/collective-responses-of-flocking-sheep-to-herding-dog.git sheepdog
python examples/public_sheep/prepare_sheep_data.py sheepdog --interval 1 --output /tmp/sheep_1s
sha256sum /tmp/sheep_1s/*.csv /tmp/sheep_1s/config.json   # compare with EXPECTED_FINGERPRINTS.txt
python src/run_analysis.py /tmp/sheep_1s/trajectories.csv --config /tmp/sheep_1s/config.json \
  --ties /tmp/sheep_1s/ties.csv --output /tmp/sheep_run
python src/verify_analysis.py /tmp/sheep_run --input trajectories=/tmp/sheep_1s/trajectories.csv \
  --input ties=/tmp/sheep_1s/ties.csv --input config=/tmp/sheep_1s/config.json
```

The same two CSV files can be uploaded on the website with "Use public sheep demo settings".

## Expected results (1-s steps, 5-m radius, leave-one-trial-out over 8 trials)

| Quantity | Value |
|---|---|
| Held-out transitions | 9,884 |
| Mean heading error: keep heading / M0 / M1 / M2 / M3 | 20.58° / 18.98° / 18.92° / 19.03° / 18.96° |
| M0 vs keep heading | −1.61° (95% interval −2.01 to −1.17) |
| M1 vs M0 | −0.06° (−0.17 to +0.05) |
| M3 vs M2 | −0.07° (−0.18 to +0.05) |

Runs with the repository's pinned library versions (Mserver) and in the browser (Pyodide)
reproduced every reported number to within 3e-8 degrees; file bytes differ only where library
versions differ. All 8 trials involve the same 14 sheep, so intervals are exploratory.
