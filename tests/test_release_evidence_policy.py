"""Evidence policy must never break historical releases or accept fake changes."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import check_release_changes as gate

class ReleaseEvidenceTests(unittest.TestCase):
    def test_historical_versions_are_exempt(self):
        self.assertFalse(gate.required("0.3.77"))
        self.assertFalse(gate.required("0.3.80"))
        self.assertTrue(gate.required("0.3.81"))

    def sample(self):
        notes=[f"[=] Изменение {i} в пользовательском интерфейсе" for i in range(10)]
        entries=[{"note":note,"path":"app/src/main/java/dev/xarkon/link/Example.java",
                  "changed_line":f"public void fixFeature{i}() {{ renderFeature{i}(); }}"}
                 for i,note in enumerate(notes)]
        return notes,{"entries":entries}

    def test_ten_distinct_changed_lines_pass(self):
        notes,evidence=self.sample()
        lines={x["changed_line"] for x in evidence["entries"]}
        self.assertEqual(gate.validate_evidence(notes,evidence,lambda p:lines),10)

    def test_missing_or_repeated_code_evidence_fails(self):
        notes,evidence=self.sample()
        with self.assertRaises(ValueError):
            gate.validate_evidence(notes,evidence,lambda p:set())
        evidence["entries"][1]["changed_line"]=evidence["entries"][0]["changed_line"]
        with self.assertRaises(ValueError):
            gate.validate_evidence(notes,evidence,lambda p:{
                x["changed_line"] for x in evidence["entries"]})

    def test_docs_and_tests_are_not_product_changes(self):
        notes,evidence=self.sample()
        evidence["entries"][0]["path"]="docs/QA_CHECKLIST_RU.md"
        with self.assertRaises(ValueError):
            gate.validate_evidence(notes,evidence,lambda p:set())

    def test_less_than_ten_is_rejected(self):
        notes,evidence=self.sample()
        with self.assertRaises(ValueError):
            gate.validate_evidence(notes[:9],{"entries":evidence["entries"][:9]},
                                   lambda p:set())
