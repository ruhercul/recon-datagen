"""Verify every scenario's BASE schema declares exactly 2 non-monetary mapping
keys + 1 monetary key.

This guards the get_table_keys_suggestion eval pipeline's schema shape. The
number of mapping keys actually *declared* at generation time is configurable
(1-3) via ``GenerationConfig.num_mapping_keys`` and is covered separately in
``test_mapping_key_variation.py``.
"""

import pytest

from recon_datagen.scenarios import SCENARIO_REGISTRY


EXPECTED_NON_MONETARY_KEYS = 2
EXPECTED_MONETARY_KEYS = 1


@pytest.mark.parametrize("scenario_name", sorted(SCENARIO_REGISTRY.keys()))
def test_scenario_declares_composite_keys(scenario_name: str) -> None:
    scenario = SCENARIO_REGISTRY[scenario_name]()

    assert len(scenario.dataset1_key_columns) == EXPECTED_NON_MONETARY_KEYS, (
        f"{scenario_name} dataset1 ({scenario.dataset1_name}) has "
        f"{len(scenario.dataset1_key_columns)} non-monetary key(s) "
        f"{scenario.dataset1_key_columns}; need exactly {EXPECTED_NON_MONETARY_KEYS}"
    )
    assert len(scenario.dataset2_key_columns) == EXPECTED_NON_MONETARY_KEYS, (
        f"{scenario_name} dataset2 ({scenario.dataset2_name}) has "
        f"{len(scenario.dataset2_key_columns)} non-monetary key(s) "
        f"{scenario.dataset2_key_columns}; need exactly {EXPECTED_NON_MONETARY_KEYS}"
    )
    assert len(scenario.dataset1_monetary_columns) == EXPECTED_MONETARY_KEYS, (
        f"{scenario_name} dataset1 monetary columns "
        f"{scenario.dataset1_monetary_columns} != {EXPECTED_MONETARY_KEYS}"
    )
    assert len(scenario.dataset2_monetary_columns) == EXPECTED_MONETARY_KEYS, (
        f"{scenario_name} dataset2 monetary columns "
        f"{scenario.dataset2_monetary_columns} != {EXPECTED_MONETARY_KEYS}"
    )

    scenario.validate_keys(
        expected_non_monetary=EXPECTED_NON_MONETARY_KEYS,
        expected_monetary=EXPECTED_MONETARY_KEYS,
    )


def test_validate_keys_raises_when_counts_differ() -> None:
    """validate_keys must surface a ValueError when expectations don't match."""
    scenario = SCENARIO_REGISTRY["bank-recon"]()
    with pytest.raises(ValueError):
        scenario.validate_keys(expected_non_monetary=99, expected_monetary=1)
    with pytest.raises(ValueError):
        scenario.validate_keys(expected_non_monetary=2, expected_monetary=99)


def test_key_columns_exclude_monetary() -> None:
    """Monetary columns must not be counted as table keys."""
    for name, cls in SCENARIO_REGISTRY.items():
        scenario = cls()
        for col_name in scenario.dataset1_key_columns:
            col = next(c for c in scenario.dataset1_schema if c.name == col_name)
            assert not col.is_monetary, (
                f"{name} dataset1 key '{col_name}' is monetary; "
                "monetary columns should not count as table keys"
            )
        for col_name in scenario.dataset2_key_columns:
            col = next(c for c in scenario.dataset2_schema if c.name == col_name)
            assert not col.is_monetary, (
                f"{name} dataset2 key '{col_name}' is monetary; "
                "monetary columns should not count as table keys"
            )
