# WP0 data governance and study inventory

No empirical sheep dataset or study-specific approvals are supplied in this repository.
Unknown fields must remain unknown. Software licensing does not grant permission to use
or release animal data. Complete `configs/study_inventory.template.json` in private storage,
not in the public checkout. The template is a checklist, not a machine-validated approval.

Keep code, raw, interim, processed, results and temporary files separate. Raw exports must
remain immutable. Use institutional access controls, backup and retention rules agreed with
the data owner. A hash detects changes but does not prevent them. Store identity crosswalks,
exact farm locations, credentials and confidential metadata only in approved private areas.
Anonymized animal IDs alone do not anonymize coordinates or times.

Before transfer, record the data owner, permitted users and purposes, ethics approval,
publication rights, embargo, consent/access restrictions, retention and deletion rules.
Retain the original device export, checksum, collection protocol, device/firmware version,
clock synchronization and sensor accuracy evidence. Record every transformation in code.

`src/audit_trajectories.py` audits a metric-schema CSV without fitting or changing it and
writes diagnostics even when structural validation fails (exit status 2). It does not
certify time zones, metric units, biological independence or privacy. For raw GPS/device
exports, preserve the original file and write a documented adapter into private interim
storage before using the six-column structural audit. The integrated analysis accepts
WGS84 GPS directly with an explicitly selected projected metre CRS.

`.gitignore` reduces accidental commits in common private folders. It does not stop force
adds, previously tracked files or sensitive content saved under other names. Review staged
changes before every commit. All analysis exports, including figures, summaries, networks
and `analysis_bundle.json`, require disclosure review. The bundle can contain group IDs and
small-group scores; it is not automatically safe for a public website.
