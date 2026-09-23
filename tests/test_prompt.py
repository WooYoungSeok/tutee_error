"""Prompt rendering: the three placeholders, and nothing else."""

import pytest

from errdesc.config import load_config, prompt_path
from errdesc.prompt import PromptError, load_prompt, render_prompt


def test_confirmed_prompt_loads_with_all_placeholders():
    template, digest = load_prompt(prompt_path(load_config()))
    assert len(digest) == 64
    for name in ("{question}", "{incorrect_solution}", "{source_error_label}"):
        assert name in template


def test_json_braces_in_template_are_preserved():
    template, _ = load_prompt(prompt_path(load_config()))
    rendered = render_prompt(
        template,
        {"question": "Q", "incorrect_solution": "R", "source_error_label": "A"},
    )
    assert '"status": "ok | ambiguous | label_conflict"' in rendered
    assert rendered.endswith("A\n")
    assert "{question}" not in rendered


def test_substituted_text_is_not_rescanned():
    template = "Q={question}\nR={incorrect_solution}\nA={source_error_label}"
    rendered = render_prompt(
        template,
        {
            "question": "{incorrect_solution}",
            "incorrect_solution": "{source_error_label}",
            "source_error_label": "label",
        },
    )
    assert rendered == "Q={incorrect_solution}\nR={source_error_label}\nA=label"


def test_curly_braces_in_input_survive():
    template = "R={incorrect_solution}"
    rendered = render_prompt(
        template,
        {"question": "", "incorrect_solution": "{a: 1} \\frac{1}{2}", "source_error_label": ""},
    )
    assert rendered == "R={a: 1} \\frac{1}{2}"


def test_missing_value_raises():
    with pytest.raises(PromptError):
        render_prompt("{question}", {"question": "q"})
