"""Check exported Client Scripts for encoding corruption; use --write to repair.

Party queries belong in the DocType JS. Never inject another copy into fixtures.
"""

import argparse
import json
from pathlib import Path

from solar2.text_encoding import repair_text


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--write", action="store_true")
	args = parser.parse_args()
	path = Path(__file__).resolve().parent / "solar2/fixtures/client_script.json"
	rows = json.loads(path.read_text(encoding="utf-8"))
	fixed = [
		{key: repair_text(value) if isinstance(value, str) else value for key, value in row.items()}
		for row in rows
	]
	if len({row["name"] for row in fixed}) != len(fixed):
		raise SystemExit("Duplicate script names after decoding; reconcile duplicates before exporting.")
	if fixed == rows:
		print("Client Script fixture encoding is clean.")
	elif args.write:
		path.write_text(json.dumps(fixed, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
		print("Repaired Client Script fixture encoding.")
	else:
		raise SystemExit("Corrupted Client Script text found; run with --write to repair.")


if __name__ == "__main__":
	main()
