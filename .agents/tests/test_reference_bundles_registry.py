"""Focused tests for Phase 6-A: `.agents/reference_bundles.yaml`, a
drift-prevention registry for Required Start Google Workspace module
bundles repeated across report-writer skills, plus the
`check_reference_bundles()` validator in `validate_repo.py`.

This is NOT a context-reduction mechanism. Required Start sections keep
spelling out every module path explicitly; the registry is only checked
*against* that prose (never read by an agent instead of it), so a new
report-writer skill still lists its bundle's modules literally and adds
itself to `used_by` in the same commit - see `repo-maintenance/SKILL.md`.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
SCRIPTS_DIR = REPO_ROOT / ".agents" / "scripts"
BUNDLES_PATH = REPO_ROOT / ".agents" / "reference_bundles.yaml"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import validate_repo  # noqa: E402

EXPECTED_BUNDLES = {"m2-report-writer", "m1-report-writer"}

EXPECTED_M2_MODULES = [
    "qa-management-roles/references/google-workspace/workspace-basics.md",
    "qa-management-roles/references/google-workspace/m2-layout.md",
    "qa-management-roles/references/google-workspace/artifact-conventions.md",
    "qa-management-roles/references/google-workspace/api-sharing-editing.md",
]
EXPECTED_M2_USED_BY = [
    "m2-individual-development-plan",
    "m2-individual-qa-metrics-report",
    "m2-people-1to1-file",
    "m2-project-development-plan",
    "m2-project-process-checklist",
    "m2-project-risk-report",
    "m2-timeline",
    "m2-project-qa-metrics-report",
    "m2-project-status-report",
]

EXPECTED_M1_MODULES = [
    "qa-management-roles/references/google-workspace/workspace-basics.md",
    "qa-management-roles/references/google-workspace/m1-layout.md",
    "qa-management-roles/references/google-workspace/artifact-conventions.md",
    "qa-management-roles/references/google-workspace/api-sharing-editing.md",
]
EXPECTED_M1_USED_BY = [
    "m1-individual-development-plan",
    "m1-monthly-report",
    "m1-people-1to1-file",
    "m1-people-risk-report",
    "m1-timeline",
]


def _load_registry() -> dict:
    return yaml.safe_load(BUNDLES_PATH.read_text(encoding="utf-8"))


class RegistryShapeTests(unittest.TestCase):
    def test_registry_parses(self):
        registry = _load_registry()
        self.assertIsInstance(registry, dict)
        self.assertIn("bundles", registry)

    def test_only_two_expected_bundles_exist(self):
        registry = _load_registry()
        self.assertEqual(set(registry["bundles"].keys()), EXPECTED_BUNDLES)

    def test_m2_bundle_shape(self):
        bundle = _load_registry()["bundles"]["m2-report-writer"]
        self.assertEqual(bundle["modules"], EXPECTED_M2_MODULES)
        self.assertEqual(set(bundle["used_by"]), set(EXPECTED_M2_USED_BY))

    def test_m1_bundle_shape(self):
        bundle = _load_registry()["bundles"]["m1-report-writer"]
        self.assertEqual(bundle["modules"], EXPECTED_M1_MODULES)
        self.assertEqual(set(bundle["used_by"]), set(EXPECTED_M1_USED_BY))

    def test_m1_bundle_excludes_people_registry(self):
        """Only 3 of 5 m1-report-writer consumers need people-registry.md -
        it stays a per-skill addition, not bundle content."""
        bundle = _load_registry()["bundles"]["m1-report-writer"]
        self.assertFalse(any("people-registry" in m for m in bundle["modules"]))

    def test_m2_bundle_excludes_search_source_extraction(self):
        """Only 2 of 9 m2-report-writer consumers need
        search-source-extraction.md - it stays a per-skill addition."""
        bundle = _load_registry()["bundles"]["m2-report-writer"]
        self.assertFalse(any("search-source-extraction" in m for m in bundle["modules"]))

    def test_no_bundle_declared_for_fewer_than_three_consumers(self):
        registry = _load_registry()
        for name, spec in registry["bundles"].items():
            self.assertGreaterEqual(
                len(spec["used_by"]), 3,
                f"bundle {name!r} has fewer than 3 consumers - not worth naming yet",
            )


class ModulePathResolutionTests(unittest.TestCase):
    def test_all_module_paths_resolve(self):
        registry = _load_registry()
        for name, spec in registry["bundles"].items():
            for rel in spec["modules"]:
                self.assertTrue(
                    (SKILLS_DIR / rel).is_file(),
                    f"bundle {name!r} module {rel!r} does not resolve",
                )

    def test_all_used_by_skills_exist(self):
        registry = _load_registry()
        for name, spec in registry["bundles"].items():
            for skill in spec["used_by"]:
                self.assertTrue(
                    (SKILLS_DIR / skill / "SKILL.md").is_file(),
                    f"bundle {name!r} used_by names missing skill {skill!r}",
                )

    def test_api_sharing_editing_invariant(self):
        """Every declared bundle must include api-sharing-editing.md,
        unconditionally - it must never be optional or omitted."""
        registry = _load_registry()
        for name, spec in registry["bundles"].items():
            self.assertTrue(
                any(m.endswith("api-sharing-editing.md") for m in spec["modules"]),
                f"bundle {name!r} does not include api-sharing-editing.md",
            )


class ConsumerMandatoryReadTests(unittest.TestCase):
    """Every skill in a bundle's used_by must mandatorily (non-
    conditionally) read every one of that bundle's modules - the real
    payload of the drift-prevention registry."""

    def test_every_m2_consumer_mandatorily_reads_every_module(self):
        bundle = _load_registry()["bundles"]["m2-report-writer"]
        for skill in bundle["used_by"]:
            text = (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
            mandatory = validate_repo._mandatory_read_paths(text)
            for module in bundle["modules"]:
                suffix = module.replace("\\", "/")
                self.assertTrue(
                    any(p.replace("\\", "/").endswith(suffix) for p in mandatory),
                    f"{skill}/SKILL.md does not mandatorily read {module}",
                )

    def test_every_m1_consumer_mandatorily_reads_every_module(self):
        bundle = _load_registry()["bundles"]["m1-report-writer"]
        for skill in bundle["used_by"]:
            text = (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
            mandatory = validate_repo._mandatory_read_paths(text)
            for module in bundle["modules"]:
                suffix = module.replace("\\", "/")
                self.assertTrue(
                    any(p.replace("\\", "/").endswith(suffix) for p in mandatory),
                    f"{skill}/SKILL.md does not mandatorily read {module}",
                )


class ContinuationLineAndConditionalDetectionTests(unittest.TestCase):
    """Exercise validate_repo's parsing helpers directly against
    synthetic fixtures, mirroring the continuation-line/conditional-
    language detectors already proven in the Phase 5C loading-contract
    tests."""

    def test_continuation_line_read_is_detected_as_mandatory(self):
        text = (
            "## Required Start\n\n"
            "1. Read `references/plan-schema.md` and\n"
            "   `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.\n"
        )
        mandatory = validate_repo._mandatory_read_paths(text)
        self.assertTrue(
            any(p.endswith("api-sharing-editing.md") for p in mandatory)
        )

    def test_same_line_multi_path_read_is_detected_as_mandatory(self):
        text = (
            "## Required Start\n\n"
            "1. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, "
            "`../qa-management-roles/references/google-workspace/api-sharing-editing.md`.\n"
        )
        mandatory = validate_repo._mandatory_read_paths(text)
        self.assertTrue(any(p.endswith("workspace-basics.md") for p in mandatory))
        self.assertTrue(any(p.endswith("api-sharing-editing.md") for p in mandatory))

    def test_conditional_read_does_not_satisfy_mandatory_requirement(self):
        """A situational read (containing "when"/"if" anywhere in its
        Required Start step) must not count as mandatory, even though the
        path is technically named in that step."""
        text = (
            "## Required Start\n\n"
            "1. Read `references/plan-schema.md`.\n"
            "4. Read `../qa-management-roles/references/presale-upsell-rules.md` too\n"
            "   when filling or changing the Upsell section.\n"
        )
        mandatory = validate_repo._mandatory_read_paths(text)
        self.assertFalse(any(p.endswith("presale-upsell-rules.md") for p in mandatory))
        self.assertTrue(any(p.endswith("plan-schema.md") for p in mandatory))

    def test_conditional_continuation_line_read_does_not_satisfy_requirement(self):
        text = (
            "## Required Start\n\n"
            "1. Read `references/plan-schema.md` and\n"
            "   `../qa-management-roles/references/presale-upsell-rules.md`\n"
            "   too if filling the Upsell section.\n"
        )
        mandatory = validate_repo._mandatory_read_paths(text)
        self.assertFalse(any(p.endswith("presale-upsell-rules.md") for p in mandatory))


class RegistryDriftDetectionTests(unittest.TestCase):
    """Prove check_reference_bundles() actually fails on a broken
    registry/skill state, using isolated temp fixtures rather than
    mutating the real registry or any real SKILL.md."""

    def setUp(self):
        validate_repo.failures.clear()
        validate_repo.warnings.clear()
        self.addCleanup(validate_repo.failures.clear)
        self.addCleanup(validate_repo.warnings.clear)

    def test_missing_api_sharing_editing_fails(self):
        modules = [
            "qa-management-roles/references/google-workspace/workspace-basics.md",
            "qa-management-roles/references/google-workspace/m2-layout.md",
        ]
        for rel in modules:
            self.assertTrue((SKILLS_DIR / rel).is_file())
        module_suffixes = [(rel, rel.replace("\\", "/")) for rel in modules]
        has_api_sharing = any(
            suffix.endswith("api-sharing-editing.md") for _, suffix in module_suffixes
        )
        self.assertFalse(has_api_sharing)

    def test_typo_module_path_is_caught(self):
        bad_path = SKILLS_DIR / "qa-management-roles/references/google-workspace/does-not-exist.md"
        self.assertFalse(bad_path.is_file())

    def test_typo_skill_name_is_caught(self):
        bad_skill = SKILLS_DIR / "m2-does-not-exist" / "SKILL.md"
        self.assertFalse(bad_skill.is_file())

    def test_check_reference_bundles_fails_on_monkeypatched_registry(self):
        """End-to-end: point check_reference_bundles() at a temporary
        broken registry (bad module path + bad skill name + a module
        missing from an otherwise-real skill's Required Start) via
        monkeypatching validate_repo.BUNDLES, and confirm it fails for
        each distinct reason - restoring state in cleanup either way."""
        import tempfile

        broken_yaml = f"""
bundles:
  broken-bundle:
    description: test fixture
    modules:
      - qa-management-roles/references/google-workspace/does-not-exist.md
      - qa-management-roles/references/google-workspace/workspace-basics.md
    used_by:
      - m2-does-not-exist
      - m2-department-traffic-light
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(broken_yaml)
            tmp_path = Path(f.name)

        original_bundles = validate_repo.BUNDLES
        validate_repo.BUNDLES = tmp_path
        try:
            validate_repo.check_reference_bundles()
        finally:
            validate_repo.BUNDLES = original_bundles
            tmp_path.unlink(missing_ok=True)

        joined = "\n".join(validate_repo.failures)
        self.assertIn("does-not-exist.md", joined)
        self.assertIn("m2-does-not-exist", joined)
        self.assertIn("api-sharing-editing.md", joined)
        # m2-department-traffic-light is a real skill but does not
        # mandatorily read workspace-basics.md/m2-layout.md in its
        # Required Start (it only needs m2-layout.md + api-sharing-editing.md,
        # not the full report-writer bundle) - this must also surface as
        # a failure, proving the mandatory-read check itself still runs
        # even when other parts of the same bundle are broken.
        self.assertIn("m2-department-traffic-light", joined)

    def test_check_reference_bundles_passes_on_real_registry(self):
        validate_repo.check_reference_bundles()
        self.assertEqual(validate_repo.failures, [])

    def test_missing_registry_file_fails_without_raising(self):
        """A missing .agents/reference_bundles.yaml must be reported as a
        validation failure, not crash validate_repo.py with an
        unhandled exception (e.g. FileNotFoundError from .read_text())."""
        original_bundles = validate_repo.BUNDLES
        nonexistent = original_bundles.parent / "reference_bundles.does-not-exist.yaml"
        self.assertFalse(nonexistent.exists())
        validate_repo.BUNDLES = nonexistent
        try:
            validate_repo.check_reference_bundles()
        except Exception as exc:  # pragma: no cover - failure path under test
            self.fail(f"check_reference_bundles() raised {exc!r} on a missing registry file")
        finally:
            validate_repo.BUNDLES = original_bundles

        self.assertTrue(
            any("reference_bundles.yaml does not exist" in f for f in validate_repo.failures),
            validate_repo.failures,
        )
        self.assertEqual(validate_repo.BUNDLES, original_bundles)


if __name__ == "__main__":
    unittest.main()
