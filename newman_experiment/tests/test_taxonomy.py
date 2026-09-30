"""Taxonomy: the confirmed 16/10 mapping, dataset-scoped aliases, N = mapping(E), and the workbook check."""

from __future__ import annotations

import copy

import pytest

from newman.common import resolve, sha256_file
from newman.taxonomy import (
    EXCLUDED,
    EXPECTED_PER_STAGE,
    Taxonomy,
    TaxonomyError,
    parse_decision,
    verify_workbook,
)

TAX = Taxonomy.load(resolve("configs/taxonomy.yaml"))

# plan 3.1 / 3.2 (user-confirmed column D), independent of the YAML file
PLAN_STAGES = {
    "mathedu.wrong_mathematical_operation_concept": "transformation", "mathedu.comprehension_error": "comprehension",
    "mathedu.arithmetical_error": "process_skills", "mathedu.algebraic_error": "process_skills",
    "mathedu.measurement_error": "transformation", "mathclean.logic_error": "transformation",
    "mathclean.computing_error": "process_skills", "eic.calculation_error": "process_skills",
    "eic.referencing_context_value_error": "reading", "eic.referencing_previous_step_value_error": "process_skills",
    "eic.unit_conversion_error": "transformation", "eic.operator_error": "transformation",
    "eic.confusing_formula_error": "transformation", "eic.adding_irrelevant_information": "reading",
    "stepwise.calculation_error_easily_solved_by_a_calculator": "process_skills",
    "stepwise.misunderstanding_of_a_question": "comprehension",
}
PLAN_EXCLUDED = {"mathedu.unfinished_answer", "mathedu.lack_of_necessary_mathematical_concepts", "mathedu.careless_error",
                 "mathclean.expression_error", "eic.counting_error", "eic.missing_step",
                 "stepwise.extra_quantity_or_missing_quantity", "stepwise.missing_or_wrong_factual_knowledge",
                 "stepwise.reached_correct_solution_but_proceeded_further", "stepwise.unit_conversion_error"}


def test_mapping_equals_the_plan():
    assert {t.id: t.newman_stage for t in TAX.types.values()} == PLAN_STAGES
    assert set(TAX.excluded) == PLAN_EXCLUDED
    assert {s: sum(1 for v in PLAN_STAGES.values() if v == s) for s in EXPECTED_PER_STAGE} == EXPECTED_PER_STAGE
    assert "encoding" not in TAX.stages


def test_stage_always_follows_the_type():
    for tid in TAX.adopted_ids():
        c = TAX.condition(tid)
        assert c["stage_id"] == PLAN_STAGES[tid]
        assert c["stage_name"] == TAX.stages[PLAN_STAGES[tid]].name
        assert set(TAX.prompt_values(tid)) == {"newman_framework", "newman_stage_name", "newman_stage_definition",
                                               "source_error_name", "source_error_definition"}
    assert TAX.framework.startswith("Newman's Error Analysis (Newman, 1977, 1983)")


def test_labels_resolve_inside_their_dataset_only():
    assert TAX.resolve("eic", "unit_conversion_error") == ("adopted", "eic.unit_conversion_error")
    assert TAX.resolve("stepwise", "Unit conversion error") == (EXCLUDED, "stepwise.unit_conversion_error")
    assert TAX.resolve("eic", "Unit conversion error") == ("unknown", None)          # no cross-dataset or case merging
    assert TAX.resolve("mathedu", "Wrong mathematical operation/concept")[0] == "adopted"
    assert TAX.resolve("mathedu", "Wrong Mathematical Operation/Concept") == ("unknown", None)   # only listed aliases
    assert TAX.types["eic.unit_conversion_error"].name == "Unit Conversion Error"
    assert TAX.excluded["stepwise.unit_conversion_error"].name == "Unit conversion error"
    assert TAX.resolve("mathclean", "expression error") == (EXCLUDED, "mathclean.expression_error")


def test_unit_related_types_are_exactly_the_two_of_the_plan():
    assert {t.id for t in TAX.types.values() if t.unit_related} == {"mathedu.measurement_error", "eic.unit_conversion_error"}


def test_inconsistent_taxonomy_is_rejected():
    raw = copy.deepcopy(TAX.raw)
    raw["error_types"][0]["newman_stage"] = "reading"
    with pytest.raises(TaxonomyError):
        Taxonomy(raw)
    raw = copy.deepcopy(TAX.raw)
    raw["excluded_types"][0]["source_aliases"] = raw["error_types"][0]["source_aliases"]
    raw["excluded_types"][0]["dataset"] = raw["error_types"][0]["dataset"]
    with pytest.raises(TaxonomyError):
        Taxonomy(raw)


@pytest.mark.parametrize("cell, expected", [
    ("Transformation(9)", ("transformation", "(9)")), ("Process Skills", ("process_skills", "")),
    ("process skills", ("process_skills", "")), ("Reading", ("reading", "")), ("Comprehension ", ("comprehension", "")),
    ("제외(85)", (EXCLUDED, "(85)")), ("제외 - 100*2", (EXCLUDED, "- 100*2")),
])
def test_decision_cells(cell, expected):
    assert parse_decision(cell, TAX) == expected


def test_unknown_decision_cell_is_an_error():
    with pytest.raises(TaxonomyError):
        parse_decision("Encoding", TAX)
    with pytest.raises(TaxonomyError):
        parse_decision("Readings?", TAX)


# --- workbook ----------------------------------------------------------------------------

STAGE_CELL = {"reading": "Reading", "comprehension": "Comprehension", "transformation": "Transformation(9)",
              "process_skills": "Process Skills"}


def make_workbook(path, flip=None, other_header="혁규 분류", definition_edit=None):
    """The real layout: A 라벨명, B 라벨 설명, C 혁규 분류, D 영석 분류, no dataset column."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Newman 재분류"
    ws.append(["라벨명", "라벨 설명", other_header, "영석 분류", "판단 보류 항목의 복수 후보", "분류 근거"])
    for item in sorted(TAX.all_items(), key=lambda t: (t.dataset, t.id)):
        decision = "제외 - 100*2" if item.id in TAX.excluded else STAGE_CELL[item.newman_stage]
        if item.id == flip:
            decision = "Reading" if decision != "Reading" else "Process Skills"
        definition = TAX.types[item.id].definition if item.id in TAX.types else "an excluded label"
        if item.id == definition_edit:
            definition = (definition or "") + " (edited)"
        ws.append([item.name, definition, "Process Skills", decision, None, None])
    wb.create_sheet("분류 근거").append(["라벨명", "Newman 분류"])
    wb.save(path)


def taxonomy_for(path):
    raw = copy.deepcopy(TAX.raw)
    raw["mapping_source"]["sha256"] = sha256_file(path)
    return Taxonomy(raw)


def test_workbook_that_matches_is_verified(tmp_path):
    wb = tmp_path / "mapping.xlsx"
    make_workbook(wb)
    report = verify_workbook(wb, taxonomy_for(wb))
    assert report["problems"] == [] and report["verified"]
    assert report["types"]["eic.unit_conversion_error"]["decision"] == "transformation"      # 'Unit Conversion Error'
    assert report["types"]["stepwise.unit_conversion_error"]["decision"] == EXCLUDED         # 'Unit conversion error'
    assert report["types"]["mathedu.measurement_error"]["mapping_cell_raw"] == "Transformation(9)"
    assert len(report["types"]) == 26


def test_workbook_disagreement_hash_definition_and_header_are_reported(tmp_path):
    wb = tmp_path / "mapping.xlsx"
    make_workbook(wb, flip="eic.operator_error")
    report = verify_workbook(wb, taxonomy_for(wb))
    assert any("eic.operator_error" in p for p in report["problems"]) and not report["verified"]
    make_workbook(wb, definition_edit="eic.calculation_error")
    assert any("definition differs" in p for p in verify_workbook(wb, taxonomy_for(wb))["problems"])
    make_workbook(wb)
    assert any("sha256" in p for p in verify_workbook(wb, TAX)["problems"])   # the real expected hash differs
    make_workbook(wb, other_header="메모")
    assert any("혁규" in p for p in verify_workbook(wb, taxonomy_for(wb))["problems"])


def test_nfd_file_name_is_found(tmp_path):
    import unicodedata

    from newman.taxonomy import find_file

    name = "Newman_relabeling_영석_마무리 (1).xlsx"
    (tmp_path / unicodedata.normalize("NFD", name)).write_bytes(b"x")
    assert find_file(tmp_path / unicodedata.normalize("NFC", name)) is not None


def test_types_without_workbook_definition():
    assert {t.id for t in TAX.types.values() if t.definition is None} == {
        "stepwise.calculation_error_easily_solved_by_a_calculator", "stepwise.misunderstanding_of_a_question"}
