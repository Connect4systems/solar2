import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from solar2.client_script_cleanup import after_migrate, before_migrate, cleanup_plan, fixture_scripts
from solar2.text_encoding import repair_text


def corrupt(value):
	# Undefined Windows-1252 bytes were retained as C1 controls in the bad export.
	result = []
	for byte in value.encode("utf-8"):
		try:
			result.append(bytes([byte]).decode("cp1252"))
		except UnicodeDecodeError:
			result.append(chr(byte))
	return "".join(result)


class EncodingTests(unittest.TestCase):
	def test_arabic_and_punctuation_round_trip(self):
		text = "نوع العملية، العميل / المورد / الموظف — مرحبًا ✅"
		self.assertEqual(repair_text(corrupt(text)), text)

	def test_double_encoding_and_mixed_correct_text(self):
		text = "العميل"
		self.assertEqual(repair_text(corrupt(corrupt(text))), text)
		self.assertEqual(repair_text("نوع: " + corrupt(text)), "نوع: " + text)

	def test_correct_text_preserved(self):
		text = "Customer العميل Øresund café £50 €60 — ✓"
		self.assertEqual(repair_text(text), text)

	def test_latin1_corruption(self):
		text = "الشركة"
		self.assertEqual(repair_text(text.encode("utf-8").decode("latin1")), text)


class CleanupTests(unittest.TestCase):
	def setUp(self):
		self.canonical = {
			"name": "Financial Movement - تبسيط التسجيل",
			"dt": "Financial Movement",
			"view": "Form",
			"enabled": 1,
			"script": "// original",
		}
		self.alias = dict(self.canonical, name=corrupt(self.canonical["name"]))
		self.fixtures = {self.canonical["name"]: self.canonical}

	def test_only_encoded_alias_is_disabled(self):
		unrelated = dict(self.alias, name="Unrelated customization")
		rows = [self.canonical, self.alias, unrelated]
		original = copy.deepcopy(rows)
		self.assertEqual(
			cleanup_plan(rows, self.fixtures),
			[
				{
					"name": self.alias["name"],
					"replacement": self.canonical["name"],
					"enabled": 0,
				}
			],
		)
		self.assertEqual(rows, original)

	def test_disabled_alias_is_idempotent(self):
		self.alias["enabled"] = 0
		self.assertEqual(cleanup_plan([self.canonical, self.alias], self.fixtures), [])

	def test_missing_replacement_aborts(self):
		with self.assertRaisesRegex(RuntimeError, "Missing canonical"):
			cleanup_plan([self.alias], self.fixtures)

	def test_disabled_replacement_aborts(self):
		canonical = dict(self.canonical, enabled=0)
		with self.assertRaisesRegex(RuntimeError, "is disabled"):
			cleanup_plan([canonical, self.alias], self.fixtures)

	def test_other_doctype_or_view_untouched(self):
		for override in ({"dt": "Other"}, {"view": "List"}):
			self.assertEqual(cleanup_plan([self.canonical, dict(self.alias, **override)], self.fixtures), [])

	def test_migration_backs_up_before_disabling_and_is_repeatable(self):
		rows = [self.canonical, self.alias]
		with tempfile.TemporaryDirectory() as directory:
			writes = []

			def set_value(doctype, name, field, value):
				backups = list(Path(directory).rglob("*.json"))
				self.assertTrue(backups)
				self.assertTrue(
					any(
						row["name"] == name and row["enabled"] == 1
						for file in backups
						for row in json.loads(file.read_text(encoding="utf-8"))
					)
				)
				self.assertEqual((doctype, field, value), ("Client Script", "enabled", 0))
				self.alias["enabled"] = value
				writes.append(name)

			fake = SimpleNamespace(
				get_all=lambda *args, **kwargs: rows,
				get_site_path=lambda *parts: str(Path(directory).joinpath(*parts)),
				get_doc=lambda dt, name: SimpleNamespace(
					as_dict=lambda: next(row for row in rows if row["name"] == name)
				),
				db=SimpleNamespace(set_value=set_value),
				clear_cache=lambda: None,
			)
			with (
				patch.dict("sys.modules", {"frappe": fake}),
				patch("solar2.client_script_cleanup.fixture_scripts", return_value=self.fixtures),
			):
				before_migrate()
				after_migrate()
				after_migrate()
			self.assertEqual(writes, [self.alias["name"]])
			self.assertEqual(self.canonical["enabled"], 1)

	def test_backup_failure_prevents_database_write(self):
		from unittest.mock import Mock

		write = Mock()
		fake = SimpleNamespace(db=SimpleNamespace(set_value=write))
		with (
			patch.dict("sys.modules", {"frappe": fake}),
			patch("solar2.client_script_cleanup.fixture_scripts", return_value=self.fixtures),
			patch("solar2.client_script_cleanup._site_rows", return_value=[self.canonical, self.alias]),
			patch("solar2.client_script_cleanup._backup", side_effect=OSError("disk full")),
		):
			with self.assertRaises(OSError):
				after_migrate()
		write.assert_not_called()

	def test_fixtures_clean_and_single_statement_generator(self):
		fixtures = fixture_scripts()
		for row in fixtures.values():
			for value in row.values():
				if isinstance(value, str):
					self.assertEqual(value, repair_text(value), row["name"])
		generators = [
			row
			for row in fixtures.values()
			if row.get("enabled")
			and row["dt"] == "Account Statement"
			and "const ast_party_map" in row["script"]
		]
		self.assertEqual(len(generators), 1)
		self.assertIn("frm.set_query('account'", generators[0]["script"])


if __name__ == "__main__":
	unittest.main()
