"""Migration cleanup for the encoding-corrupted Solar2 Client Script export.

No accounting documents or unrelated custom scripts are modified.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from solar2.text_encoding import repair_text


def fixture_scripts():
	path = Path(__file__).parent / "fixtures" / "client_script.json"
	return {row["name"]: row for row in json.loads(path.read_text(encoding="utf-8"))}


def matching_fixture(row, fixtures):
	fixture = fixtures.get(repair_text(row["name"]))
	if fixture and (row.get("dt"), row.get("view")) == (fixture["dt"], fixture["view"]):
		return fixture
	return None


def cleanup_plan(rows, fixtures):
	"""Only retire encoded aliases when their canonical replacement is present."""
	by_name = {row["name"]: row for row in rows}
	changes = []
	for row in rows:
		fixture = matching_fixture(row, fixtures)
		if not fixture or row["name"] == fixture["name"] or not row.get("enabled"):
			continue
		canonical = by_name.get(fixture["name"])
		if not canonical or not matching_fixture(canonical, fixtures):
			raise RuntimeError(f"Missing canonical Client Script for {row['name']!r}; run bench migrate.")
		if fixture.get("enabled") and not canonical.get("enabled"):
			raise RuntimeError(f"Replacement Client Script {canonical['name']!r} is disabled.")
		changes.append({"name": row["name"], "replacement": canonical["name"], "enabled": 0})
	return changes


def _site_rows():
	import frappe

	return frappe.get_all("Client Script", fields=["name", "dt", "view", "enabled", "script"])


def _backup(rows, stage):
	import frappe

	if not rows:
		return None
	directory = Path(frappe.get_site_path("private", "backups"))
	directory.mkdir(parents=True, exist_ok=True)
	stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
	path = directory / f"solar2-client-scripts-{stage}-{stamp}-{uuid4().hex[:8]}.json"
	documents = [frappe.get_doc("Client Script", row["name"]).as_dict() for row in rows]
	with path.open("x", encoding="utf-8") as output:
		json.dump(documents, output, ensure_ascii=False, indent=2, default=str)
	print(f"Solar2 Client Script backup: {path}")
	return str(path)


def before_migrate():
	"""Snapshot canonical scripts and aliases before fixture import overwrites them."""
	fixtures = fixture_scripts()
	rows = [row for row in _site_rows() if matching_fixture(row, fixtures)]
	_backup(rows, "before-migrate")


def after_migrate():
	"""Fixture import creates corrected names; retain old aliases disabled."""
	import frappe

	rows = _site_rows()
	changes = cleanup_plan(rows, fixture_scripts())
	if not changes:
		return
	names = {change["name"] for change in changes}
	_backup([row for row in rows if row["name"] in names], "before-disable")
	for change in changes:
		frappe.db.set_value("Client Script", change["name"], "enabled", 0)
		print(f"Solar2 disabled duplicate {change['name']!a}; replacement: {change['replacement']!a}")
	frappe.clear_cache()


def audit():
	"""Read-only report: bench --site SITE execute solar2.client_script_cleanup.audit."""
	fixtures = fixture_scripts()
	rows = _site_rows()
	issues = []
	by_name = {row["name"]: row for row in rows}
	for name, fixture in fixtures.items():
		row = by_name.get(name)
		if not row:
			issues.append({"name": name, "issue": "missing fixture script"})
		elif not matching_fixture(row, fixtures):
			issues.append({"name": name, "issue": "wrong DocType or view"})
		elif bool(row.get("enabled")) != bool(fixture.get("enabled")):
			issues.append({"name": name, "issue": "enabled status differs from fixture"})
		elif row.get("script", "").strip() != fixture.get("script", "").strip():
			issues.append({"name": name, "issue": "script differs from fixture"})
	for row in rows:
		if not row.get("enabled"):
			continue
		fixture = matching_fixture(row, fixtures)
		if fixture and row["name"] != fixture["name"]:
			issues.append({"name": row["name"], "issue": "enabled encoded duplicate"})
		if repair_text(row.get("script") or "") != (row.get("script") or ""):
			issues.append({"name": row["name"], "issue": "corrupted text in enabled script"})
	return {"issues": issues, "issue_count": len(issues)}
