"""Tests for the repo-maintenance pass that added a Tier 0 Baseline metric
tier and a sprint-versus-month period model (2026-09-07):

The Core 6 `qa_process_metrics` rows all assume tooling a project may not
have (a test repo, a CI run, a bug tracker). The realistic floor that is
collectable on every project is a ticket count, a story-point count, and
a git log. Those three become Tier 0: mandatory, never removable,
collected per sprint rather than per calendar month, and read as trend
against the project's own rolling three-sprint average rather than as a
comparable absolute level.

Consequences encoded here:

1. `Templates\\метрики_проекта_qa.md` §2.1 defines the three Baseline
   metrics; the former §2.1 Core 6 becomes §2.2 and is downgraded from
   unconditionally mandatory to expected-where-tooling-exists.
2. `project_metrics` gains a `Ритм спринтов` canonical context row, since
   without a sprint calendar a per-sprint period cannot be written.
3. A sprint belongs to the calendar month its end date falls in, so the
   monthly review still aggregates cleanly.
4. The earlier blanket "do not use story points / sprint throughput"
   normalization rule is reframed as level-versus-trend in both schemas.
5. `individual_metrics` carries the per-person cut of the same baseline
   (Core goes from 4 metrics to 5), with the sprint inside `Показатель`
   because that sheet has no period column.

And the follow-up layout pass (2026-09-09), after the sheet as actually
shared with a team turned out to be unreadable: `qa_process_metrics` goes
from a long 7-column table (one row per (metric, period)) to a wide one -
`Метрика`, `Пояснение`, `Owner`, then one column appended per sprint.
`Период` and `Тренд` stop being columns (the column header is the period;
the trend is what reading a row left to right shows), `Проект` goes away
as a per-row constant, the Baseline rows sit at the top under a group
label, and every tier is collected per sprint rather than Core/Extended
per calendar month.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
TEMPLATES_DIR = REPO_ROOT / "Templates"

PROJECT_CATALOG_PATH = TEMPLATES_DIR / "метрики_проекта_qa.md"
INDIVIDUAL_CATALOG_PATH = TEMPLATES_DIR / "метрики_qa_по_проекту.md"
PROCESS_SCHEMA_PATH = (
    SKILLS_DIR / "m2-project-qa-metrics-report" / "references" / "qa-process-metrics-schema.md"
)
INDIVIDUAL_SCHEMA_PATH = (
    SKILLS_DIR / "m2-individual-qa-metrics-report" / "references" / "individual-metrics-schema.md"
)
PROJECT_SKILL_PATH = SKILLS_DIR / "m2-project-qa-metrics-report" / "SKILL.md"
INDIVIDUAL_SKILL_PATH = SKILLS_DIR / "m2-individual-qa-metrics-report" / "SKILL.md"
CATALOG_PATH = SKILLS_DIR / "qa-management-roles" / "references" / "qa-metrics-catalog.md"
PROCESS_CSV_PATH = TEMPLATES_DIR / "qa_process_metrics.csv"
SCRIPTS_DIR = REPO_ROOT / ".agents" / "scripts"

BASELINE_METRICS = (
    "Тикеты за спринт (QA)",
    "Story points за спринт (QA)",
    "Git-активность за спринт (AQA)",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


class ProjectCatalogBaselineTierTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(PROJECT_CATALOG_PATH))

    def test_has_baseline_subsection(self):
        self.assertIn("### 2.1 Tier 0 — Базовые метрики", self.text)

    def test_lists_all_baseline_metrics(self):
        for metric in BASELINE_METRICS:
            self.assertIn(metric, self.text)

    def test_baseline_rows_are_never_removed(self):
        self.assertIn(
            "Правило «метрика пустует 3 спринта подряд — убираем строку» на "
            "Tier 0 **не распространяется**",
            self.text,
        )

    def test_core_six_downgraded_to_tooling_gated(self):
        self.assertIn(
            "### 2.2 Tier 1 — Core-метрики (там, где для них есть тулинг)", self.text
        )
        self.assertIn("обязательный минимум — это Tier 0", self.text)

    def test_baked_in_qa_work_counts_as_relative_value(self):
        self.assertIn("относительная величина, отдельных QA-тикетов нет", self.text)

    def test_absolute_values_not_comparable_across_projects(self):
        self.assertIn(
            "**Абсолютные значения Tier 0 несравнимы между проектами и между людьми.**",
            self.text,
        )

    def test_trend_uses_rolling_three_sprint_average(self):
        self.assertIn(
            "**Тренд читается по строке слева направо, против скользящего "
            "среднего трёх предыдущих спринтов**",
            self.text,
        )

    def test_trend_is_not_a_column(self):
        self.assertIn("Отдельной колонки `Тренд` в этом листе нет", self.text)

    def test_baseline_rows_are_project_wide_sums(self):
        self.assertIn(
            "**Здесь Tier 0 — проектные суммы, не персональные строки.**", self.text
        )


class ProjectCatalogSprintPeriodModelTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(PROJECT_CATALOG_PATH))

    def test_sprint_collects_month_reports(self):
        self.assertIn(
            "**Собираются все тиры по спринтам, единица отчётности — всегда "
            "календарный месяц**",
            self.text,
        )

    def test_sprint_belongs_to_month_of_its_end_date(self):
        self.assertIn(
            "**Спринт относится к тому календарному месяцу, в который попадает "
            "его дата окончания.**",
            self.text,
        )

    def test_sprint_is_never_split_across_months(self):
        self.assertIn("делить его между месяцами нельзя", self.text)

    def test_core_is_collected_per_sprint_too(self):
        # Changed 2026-09-09 with the sprint-per-column layout: Core/Extended
        # used to be collected per calendar month while only Tier 0 was per
        # sprint, which one column per sprint cannot express.
        self.assertIn("Одна колонка на спринт означает одну частоту сбора на весь лист", self.text)
        self.assertNotIn("остаётся **последним завершённым календарным месяцем**", self.text)

    def test_kanban_projects_fall_back_to_monthly(self):
        self.assertIn("Нет спринтов (Kanban)", self.text)
        self.assertIn("колонками становятся календарные месяцы", self.text)

    def test_wide_layout_columns_and_group_rows(self):
        self.assertIn(
            "**Широкий формат: три фиксированные колонки, дальше по одной "
            "колонке на спринт**",
            self.text,
        )
        self.assertIn("**Идентичность строки — только `Метрика`.**", self.text)
        self.assertIn("**Новый спринт — новая колонка справа**", self.text)
        self.assertIn("**Колонки `Период` нет**", self.text)
        self.assertIn("**Колонки `Тренд` нет**", self.text)
        self.assertIn("**Колонки `Проект` нет**", self.text)
        self.assertIn("[Базовые метрики: каждый спринт, обязательны на любом проекте]", self.text)
        self.assertIn("[Автоматизация: заводится, если на проекте есть автотесты]", self.text)
        self.assertIn("[Дефекты]", self.text)

    def test_sprint_cadence_is_a_canonical_context_key(self):
        self.assertIn("**`Ритм спринтов`**", self.text)
        self.assertIn("`<длина> дн., якорь <YYYY-MM-DD>, <схема нумерации>`", self.text)


class ProcessSchemaTierAndPeriodTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(PROCESS_SCHEMA_PATH))

    def test_declares_three_tiers(self):
        self.assertIn("`qa_process_metrics` has three tiers, not one flat catalog", self.text)

    def test_names_each_tier(self):
        self.assertIn("**Baseline / Tier 0 (3 metrics)**", self.text)
        self.assertIn("**Core / Tier 1 (6 metrics)**", self.text)
        self.assertIn("**Extended / Tier 2 catalog**", self.text)

    def test_every_tier_is_collected_per_sprint(self):
        self.assertIn("**Every tier is collected per sprint**", self.text)
        self.assertIn("2026-S14 (2026-08-19..2026-09-01)", self.text)

    def test_wide_sprint_per_column_layout(self):
        self.assertIn(
            "**Wide layout: three fixed columns, then one column per sprint**",
            self.text,
        )
        self.assertIn("`Метрика`, `Пояснение`, `Owner`, `<спринт 1>`", self.text)
        self.assertIn("the dedup key is now (Метрика, sprint column)", self.text)
        self.assertIn("**No `Период` column.**", self.text)
        self.assertIn("**No `Тренд` column.**", self.text)
        self.assertIn("**No `Проект` column.**", self.text)
        self.assertIn("**Trend is read across columns, not stored.**", self.text)

    def test_removal_rule_exempts_baseline(self):
        self.assertIn(
            "If a Tier 1 or Extended metric can't be collected for 3 sprints "
            "running, remove its row",
            self.text,
        )
        self.assertIn("Tier 0 rows are exempt", self.text)

    def test_story_points_reframed_as_trend_not_level(self):
        self.assertIn("are weak as **level** metrics", self.text)
        self.assertIn(
            "They are valid as **trend** metrics inside one project's own history",
            self.text,
        )

    def test_no_leftover_unconditional_calendar_month_rule(self):
        self.assertNotIn(
            "`Период` is always the last completed calendar month", self.text
        )


class IndividualBaselineTests(unittest.TestCase):
    def setUp(self):
        self.catalog = _normalized(_read(INDIVIDUAL_CATALOG_PATH))
        self.schema = _normalized(_read(INDIVIDUAL_SCHEMA_PATH))

    def test_core_count_raised_to_five(self):
        self.assertIn("Ровно 5 core-метрик.", self.catalog)

    def test_performance_metric_spells_out_tickets_and_story_points(self):
        self.assertIn("**Перформанс (тикеты и story points за спринт)**", self.catalog)

    def test_git_activity_is_a_core_row(self):
        self.assertIn("**Git-активность за спринт (AQA)**", self.catalog)

    def test_git_activity_requires_reliable_collector_validity(self):
        self.assertIn("`Metrics validity` этого человека как `Reliable`", self.catalog)

    def test_manual_stream_marks_git_not_applicable(self):
        self.assertIn("Не применимо (manual QA stream)", self.catalog)

    def test_dynamics_not_level_rule(self):
        self.assertIn(
            "**Перформанс и Git-активность — метрики динамики, не уровня.**",
            self.catalog,
        )

    def test_sprint_lives_inside_pokazatel_not_a_new_column(self):
        self.assertIn("18 тикетов / 21 SP (спринт 2026-S14, 19.08-01.09)", self.schema)
        self.assertIn("Do not add a period column", self.schema)

    def test_schema_reframes_the_old_blanket_ban(self):
        self.assertIn(
            "Closed tasks, story points, and git activity are **trend** metrics, "
            "not **level** metrics",
            self.schema,
        )
        self.assertIn("do not drop the row", self.schema)

    def test_schema_trend_rule_uses_three_sprint_average(self):
        self.assertIn(
            "compare against the rolling average of the previous three sprints",
            self.schema,
        )


class SkillEntryPointsTests(unittest.TestCase):
    def test_project_skill_points_at_tier_split(self):
        text = _normalized(_read(PROJECT_SKILL_PATH))
        self.assertIn("Baseline / Core / Extended tier split", text)
        self.assertIn("`Ритм спринтов`", text)

    def test_individual_skill_names_the_baseline_pair(self):
        text = _normalized(_read(INDIVIDUAL_SKILL_PATH))
        self.assertIn("The 5 Core rows", text)
        self.assertIn("Git-активность за спринт (AQA)", text)


class WideProcessSheetArtifactTests(unittest.TestCase):
    """The CSV template and the scaffold script must agree with the schema."""

    def test_csv_template_header_is_wide(self):
        import csv

        with open(PROCESS_CSV_PATH, encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[0][:3], ["Метрика", "Пояснение", "Owner"])
        # At least one sprint column, and every row the same width.
        self.assertGreater(len(rows[0]), 3)
        self.assertEqual({len(row) for row in rows}, {len(rows[0])})
        for dropped in ("Проект", "Период", "Тренд"):
            self.assertNotIn(dropped, rows[0])

    def test_csv_template_rows_are_grouped_baseline_first(self):
        import csv

        with open(PROCESS_CSV_PATH, encoding="utf-8", newline="") as handle:
            metrics = [row[0] for row in csv.reader(handle)][1:]
        self.assertEqual(
            metrics[0], "[Базовые метрики: каждый спринт, обязательны на любом проекте]"
        )
        self.assertEqual(metrics[1:4], list(BASELINE_METRICS))
        self.assertIn("[Автоматизация: заводится, если на проекте есть автотесты]", metrics)
        self.assertIn("[Дефекты]", metrics)

    def test_scaffold_writes_the_same_shape(self):
        import sys

        sys.path.insert(0, str(SCRIPTS_DIR))
        import scaffold_project_dashboard as module

        self.assertEqual(module.QA_PROCESS_FIXED_HEADER, ["Метрика", "Пояснение", "Owner"])
        self.assertEqual(len(module.QA_BASELINE_TEMPLATE), 3)
        self.assertEqual(len(module.QA_METRICS_TEMPLATE), 6)
        rows = module.qa_process_rows("Test Owner")
        metrics = [row[0] for row in rows]
        self.assertEqual(
            metrics[0], "[Базовые метрики: каждый спринт, обязательны на любом проекте]"
        )
        self.assertEqual(metrics[1:4], list(BASELINE_METRICS))
        # Group label rows carry no owner and no value.
        for row in rows:
            if row[0].startswith("["):
                self.assertEqual(row[1:], ["", "", ""])

    def test_formatting_profile_freezes_the_fixed_columns(self):
        import sys

        sys.path.insert(0, str(SCRIPTS_DIR))
        import format_all_sheets as module

        profile = module.PROFILES["qa_process_metrics"]
        self.assertIs(module.resolve_profile_for_tab("qa_process_metrics", "Sheet1"), profile)
        self.assertEqual(profile["freeze_columns"], 3)
        self.assertEqual(profile["freeze_rows"], 1)
        self.assertEqual(len(profile["widths"]), 3)


class CrossCuttingCatalogTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(CATALOG_PATH))

    def test_declares_four_tiers(self):
        self.assertIn("across four tiers", self.text)

    def test_baseline_tier_listed_first(self):
        self.assertIn(
            "## 1. Baseline Project QA-Process Metrics (mandatory floor, per sprint)",
            self.text,
        )
        for metric in BASELINE_METRICS:
            self.assertIn(metric, self.text)

    def test_core_tier_renumbered_and_downgraded(self):
        self.assertIn(
            "## 2. Core Minimum Project QA-Process Metrics (expected, project-level)",
            self.text,
        )

    def test_optional_tiers_renumbered(self):
        self.assertIn("## 3. Optional Project/Release Quality Metrics", self.text)
        self.assertIn("## 4. Optional Individual QA Contribution Metrics", self.text)

    def test_still_not_a_source_of_truth(self):
        self.assertIn("This is not a fifth schema to keep in sync by hand", self.text)


if __name__ == "__main__":
    unittest.main()
