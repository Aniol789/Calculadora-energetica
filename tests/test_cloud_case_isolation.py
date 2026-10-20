import tempfile
import unittest
from pathlib import Path

from case_manager import default_case, prepare_ephemeral_run_case


class CloudCaseIsolationTests(unittest.TestCase):
    def test_run_outputs_are_redirected_without_mutating_saved_case(self):
        case = default_case()
        original_output = case["OUTPUT"].copy()

        with tempfile.TemporaryDirectory() as temp_dir:
            run_case = prepare_ephemeral_run_case(case, temp_dir)
            output = run_case["OUTPUT"]

            self.assertEqual(Path(output["hourly_csv_path"]).parent, Path(temp_dir))
            self.assertEqual(Path(output["daily_csv_path"]).parent, Path(temp_dir))
            self.assertEqual(Path(output["report_html_path"]).parent, Path(temp_dir))
            self.assertEqual(Path(output["report_archive_dir"]).parent, Path(temp_dir))
            self.assertFalse(output["open_report_in_browser"])

        self.assertEqual(case["OUTPUT"], original_output)
        self.assertEqual(case["LOCATION"]["name"], "Santa Maria d'Oló")


if __name__ == "__main__":
    unittest.main()