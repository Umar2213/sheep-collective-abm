#!/usr/bin/env python3
"""Validate all stored tables and regenerate an auditable summary without simulations."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from analysis_utils import level_crossing

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'results/audit'
OUT.mkdir(parents=True, exist_ok=True)
checks = []
for path in sorted((ROOT / 'results').glob('**/*.csv')):
    if OUT in path.parents:
        continue
    d = pd.read_csv(path)
    assert not d.empty and not d.isna().any().any(), f'Missing data: {path}'
    assert np.isfinite(d.select_dtypes('number').to_numpy()).all(), f'Nonfinite: {path}'
    checks.append(dict(path=str(path.relative_to(ROOT)), rows=len(d), columns=len(d.columns),
                       sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
rep = pd.read_csv(ROOT / 'results/production/sweep_replicates.csv')
summ = pd.read_csv(ROOT / 'results/production/sweep_condition_means.csv')
fss = pd.read_csv(ROOT / 'results/fss/fss_replicates.csv')
fss_summ = pd.read_csv(ROOT / 'results/fss/fss_condition_means.csv')
assert len(rep) == 1140 and len(summ) == 57
assert len(fss) == 1520 and len(fss_summ) == 95
assert not rep.duplicated(['noise','sigma_std','seed']).any()
assert not fss.duplicated(['N','noise','sigma_std','seed']).any()
for d in [rep, fss]:
    assert d.phi.between(0, 1+1e-10).all()
    assert d.ar1.between(-1, 1).all()
assert (rep.phi_tempvar >= 0).all()
assert rep.real_mean.between(0,1).all()
assert rep.real_std.between(0,.51).all()
assert rep.frac_lo.between(0,1).all() and rep.frac_hi.between(0,1).all()
assert (rep.frac_lo + rep.frac_hi <= 1+1e-10).all()
assert (fss.phi2 >= fss.phi**2-1e-10).all()
assert (fss.phi4 >= fss.phi2**2-1e-10).all()
assert (fss.phi4 <= fss.phi2+1e-10).all()
for _, row in summ.iterrows():
    g = rep[(rep.noise==row.noise)&(rep.sigma_std==row.sigma_std)]
    assert set(g.seed) == set(range(1,21))
    values = dict(phi_mean=g.phi.mean(), phi_sd=g.phi.std(), chi_seed=200*g.phi.var(),
                  tempvar=g.phi_tempvar.mean(), ar1=g.ar1.mean(), frac_lo=g.frac_lo.mean(),
                  frac_hi=g.frac_hi.mean(), n=len(g))
    for col, value in values.items():
        assert np.isclose(row[col], value, atol=1e-10, rtol=1e-8), (col, row[col], value)
for _, row in fss_summ.iterrows():
    g = fss[(fss.N==row.N)&(fss.sigma_std==row.sigma_std)]
    assert set(g.seed) == set(range(1,17)) and set(g.noise) == {.5}
    values = dict(phi_mean=g.phi.mean(), phi_sd=g.phi.std(),
                  chi=row.N*(g.phi2.mean()-g.phi.mean()**2),
                  binder=1-g.phi4.mean()/(3*g.phi2.mean()**2), ar1=g.ar1.mean(),
                  drift=g.drift.max(), real_std=g.real_std.mean(), n=len(g))
    for col, value in values.items():
        assert np.isclose(row[col], value, atol=1e-10, rtol=1e-8), (col, row[col], value)
snap = pd.read_csv(ROOT / 'results/snapshots/snapshot_states.csv')
assert snap.groupby('sigma').size().eq(200).all()
assert snap.x.between(0,20,inclusive='left').all() and snap.y.between(0,20,inclusive='left').all()
assert snap.w.between(0,1).all()
thresholds = []
for noise, g in rep.groupby('noise'):
    matrix = g.pivot(index='seed', columns='sigma_std', values='phi').sort_index(axis=1)
    x = matrix.columns.to_numpy()
    y = matrix.to_numpy()
    rng = np.random.default_rng(260101231)
    # Whole seed curves are resampled because the original sweep reuses seed IDs.
    samples = [level_crossing(x, y[idx].mean(axis=0)) for idx in
               rng.integers(0, len(y), size=(2000,len(y)))]
    valid = np.asarray(samples)[np.isfinite(samples)]
    lo, hi = np.percentile(valid,[2.5,97.5]) if len(valid) else (None,None)
    thresholds.append(dict(noise=float(noise),sigma_at_phi_090=level_crossing(x,y.mean(axis=0)),
                           bootstrap_lo=lo,bootstrap_hi=hi,bracketed_bootstraps=len(valid),
                           bootstrap_count=2000))
pd.DataFrame(thresholds).to_csv(OUT/'thresholds.csv',index=False)
flags = fss[fss.drift>.02].sort_values(['N','sigma_std','seed'])
flags.to_csv(OUT/'fss_runs_requiring_stationarity_review.csv',index=False)
report = dict(source_tables=checks, production_runs=len(rep), fss_runs=len(fss),
              fss_drift_over_002=len(flags), fss_max_drift=float(fss.drift.max()),
              production_real_mean_range=[float(rep.real_mean.min()),float(rep.real_mean.max())],
              thresholds=thresholds,
              scope='Stored-data consistency only; no proof of simulation provenance or stationarity.')
(OUT/'data_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'PASS: {len(checks)} source tables, all production/FSS summary fields match replicates.')
print(f'WARNING: {len(flags)}/{len(fss)} FSS runs exceed drift 0.02; max={fss.drift.max():.6f}.')
print(pd.DataFrame(thresholds).to_string(index=False))
