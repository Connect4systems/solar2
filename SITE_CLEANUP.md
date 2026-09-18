# Apply the Arabic text and Client Script repair

The damaged text came from UTF-8 being decoded as Windows-1252 in the Client
Script fixture. Garbled script names were imported as new records alongside the
original Arabic names. This caused duplicate JavaScript declarations. The helper
scripts also replaced correct field labels with garbled labels.

This repair restores the fixture's text, scopes script helpers, removes redundant
cross-form handler registrations, and disables the older Account Statement
generator in favor of the version that also filters accounts.

## Deploy

Deploy this working tree to the server's `apps/solar2` first. These commands must
run **on the server, from its bench directory**. Use the actual bench site name
if it differs from the public hostname.

```bash
bench --site solar.connect4systems.com backup --with-files
bench --site solar.connect4systems.com migrate
bench --site solar.connect4systems.com clear-cache
bench restart
bench --site solar.connect4systems.com execute solar2.client_script_cleanup.audit
```

Stop if a command fails and retain its full output. Do not use `--skip-failing`.

`migrate` imports the corrected fixtures and runs the cleanup hooks. Clearing
cache alone does not update saved scripts. Frappe's migration sequence imports
fixtures before running `after_migrate`:
[Frappe migration implementation](https://github.com/frappe/frappe/blob/version-15/frappe/migrate.py).

Before fixture import, the hook backs up matching scripts (including their
current site edits and enabled states) to `private/backups/solar2-client-scripts-*.json`.
After import, it disables encoded aliases only when the matching canonical name,
DocType and view exist. A second snapshot is written before disabling aliases.
No script records are deleted. Accounting documents and transactions are not
changed. Normal fixture import replaces app-managed scripts with this repository's
versions; review any site-only edits against the saved snapshot.

Disabled scripts are excluded from subsequent fixture exports to avoid shipping
the archived aliases again. Do not re-enable those aliases or the older
`Account Statement - Generator`.

## Verify

The audit should return `issue_count: 0`. Any reported script differences or
remaining corrupted scripts need review; the audit does not modify them.

Hard-refresh the browser, then open Financial Movement, Sales Invoice, Purchase
Invoice, and Account Statement. Confirm Arabic labels display correctly and no
Client Script errors appear. Check the party selector on a new Financial Movement
and confirm that existing invoice project links still display correctly. Full
posting behavior requires validation on a staging site with Frappe/ERPNext.

## Local checks

```bash
python -m unittest discover -s tests -v
python tools_fix_fixture.py
node tests/check_client_scripts.cjs
```

The fixture utility checks encoding by default. `--write` repairs encoding only;
it no longer injects another copy of the party-query script.
