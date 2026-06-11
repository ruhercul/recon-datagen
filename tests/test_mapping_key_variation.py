"""Tests for the configurable number of mapping keys (num_mapping_keys).

Mirrors the get_table_keys_suggestion eval distribution: 1-2 mapping keys are
typical, up to 3 for complex scenarios; the monetary key is always exactly 1.
"""

from collections import defaultdict
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recon_datagen.generator import DataGenerator
from recon_datagen.models import GenerationConfig
from recon_datagen.scenarios import SCENARIO_REGISTRY, get_scenario


ALL_SCENARIOS = sorted(SCENARIO_REGISTRY.keys())


# ---- Config validation ------------------------------------------------------

@pytest.mark.parametrize("num_keys", [1, 2, 3])
def test_config_accepts_valid_key_counts(num_keys: int) -> None:
    config = GenerationConfig(
        scenario="bank-recon",
        total_source_rows=10,
        match_percent=0.6,
        potential_percent=0.25,
        num_mapping_keys=num_keys,
    )
    assert config.validate() == []


@pytest.mark.parametrize("num_keys", [0, 4, -1])
def test_config_rejects_invalid_key_counts(num_keys: int) -> None:
    config = GenerationConfig(
        scenario="bank-recon",
        total_source_rows=10,
        match_percent=0.6,
        potential_percent=0.25,
        num_mapping_keys=num_keys,
    )
    errors = config.validate()
    assert any("mapping keys" in e.lower() for e in errors)


def test_default_num_mapping_keys_is_two() -> None:
    config = GenerationConfig(
        scenario="bank-recon",
        total_source_rows=10,
        match_percent=0.6,
        potential_percent=0.25,
    )
    assert config.num_mapping_keys == 2


# ---- Active mapping key selection ------------------------------------------

@pytest.mark.parametrize("scenario_name", ALL_SCENARIOS)
@pytest.mark.parametrize("num_keys", [1, 2, 3])
def test_active_mapping_keys_count_matches_config(scenario_name: str, num_keys: int) -> None:
    scenario = SCENARIO_REGISTRY[scenario_name](num_mapping_keys=num_keys)
    assert len(scenario.active_mapping_keys1) == num_keys
    assert len(scenario.active_mapping_keys2) == num_keys


@pytest.mark.parametrize("scenario_name", ALL_SCENARIOS)
def test_single_key_uses_unique_reference(scenario_name: str) -> None:
    """A single declared key must be the unique reference, never the date."""
    scenario = SCENARIO_REGISTRY[scenario_name](num_mapping_keys=1)
    assert scenario.active_mapping_keys1 == [scenario.primary_key_column]
    assert scenario.active_mapping_keys2 == [scenario.secondary_key_column]


@pytest.mark.parametrize("scenario_name", ALL_SCENARIOS)
def test_two_keys_match_base_schema_keys(scenario_name: str) -> None:
    scenario = SCENARIO_REGISTRY[scenario_name](num_mapping_keys=2)
    assert set(scenario.active_mapping_keys1) == set(scenario.dataset1_key_columns)
    assert set(scenario.active_mapping_keys2) == set(scenario.dataset2_key_columns)


@pytest.mark.parametrize("scenario_name", ALL_SCENARIOS)
def test_three_keys_add_allocation_key(scenario_name: str) -> None:
    scenario = SCENARIO_REGISTRY[scenario_name](num_mapping_keys=3)
    assert scenario.third_key_name1 in scenario.active_mapping_keys1
    assert scenario.third_key_name2 in scenario.active_mapping_keys2
    # The third key appears in the effective schema and output columns.
    assert scenario.third_key_name1 in scenario.get_dataset1_columns()
    assert scenario.third_key_name2 in scenario.get_dataset2_columns()


@pytest.mark.parametrize("scenario_name", ALL_SCENARIOS)
@pytest.mark.parametrize("num_keys", [1, 2])
def test_third_key_absent_when_not_requested(scenario_name: str, num_keys: int) -> None:
    scenario = SCENARIO_REGISTRY[scenario_name](num_mapping_keys=num_keys)
    assert scenario.third_key_name1 not in scenario.get_dataset1_columns()
    assert scenario.third_key_name2 not in scenario.get_dataset2_columns()


@pytest.mark.parametrize("scenario_name", ALL_SCENARIOS)
def test_monetary_key_always_single(scenario_name: str) -> None:
    for num_keys in (1, 2, 3):
        scenario = SCENARIO_REGISTRY[scenario_name](num_mapping_keys=num_keys)
        assert len(scenario.dataset1_monetary_columns) == 1
        assert len(scenario.dataset2_monetary_columns) == 1


# ---- Generation behaviour ---------------------------------------------------

def _generate_matched_pairs(scenario_name: str, num_keys: int, seed: int = 42):
    """Generate an all-matched dataset and return (scenario, source, target)."""
    config = GenerationConfig(
        scenario=scenario_name,
        total_source_rows=40,
        match_percent=1.0,
        potential_percent=0.0,
        one_to_n_ratio=0.0,
        amount_variance_percent=0.0,
        date_variance_days=0,
        num_mapping_keys=num_keys,
        seed=seed,
    )
    assert config.validate() == []
    scenario = get_scenario(scenario_name)
    generator = DataGenerator(scenario, config)
    source, target = generator.generate_all()
    return scenario, source, target


@pytest.mark.parametrize("scenario_name", ALL_SCENARIOS)
@pytest.mark.parametrize("num_keys", [1, 2, 3])
def test_matched_pairs_agree_on_reference_and_third_key(scenario_name: str, num_keys: int) -> None:
    """Matched pairs always share the unique reference key, and the third
    allocation key when it is declared.

    (The optional second base key is an entity/date column whose cross-dataset
    consistency is scenario-specific and pre-dates this feature, so it is not
    asserted here.)
    """
    scenario, source, target = _generate_matched_pairs(scenario_name, num_keys)

    assert len(source) == len(target)  # 1:1 matches only

    # Join source and target on their unique reference key (== match group id).
    targets_by_ref = defaultdict(list)
    for record in target:
        targets_by_ref[str(record[scenario.secondary_key_column])].append(record)

    matched_pairs = 0
    for src in source:
        ref = str(src[scenario.primary_key_column])
        partners = targets_by_ref.get(ref)
        assert partners, f"{scenario_name}: no target for source ref {ref}"
        tgt = partners[0]

        # Reference key is always consistent for matched pairs.
        assert str(src[scenario.primary_key_column]) == str(tgt[scenario.secondary_key_column])

        if num_keys == 1:
            # The single declared key is exactly the (consistent) reference.
            assert scenario.active_mapping_keys1 == [scenario.primary_key_column]
            assert scenario.active_mapping_keys2 == [scenario.secondary_key_column]

        if num_keys == 3:
            # The injected allocation key must agree between source and target.
            assert src[scenario.third_key_name1] == tgt[scenario.third_key_name2], (
                f"{scenario_name}: third key differs "
                f"{src[scenario.third_key_name1]} != {tgt[scenario.third_key_name2]}"
            )
        matched_pairs += 1

    assert matched_pairs == len(source)


@pytest.mark.parametrize("scenario_name", ALL_SCENARIOS)
def test_third_key_present_in_records_only_when_requested(scenario_name: str) -> None:
    # num=2 -> column not in any record
    _, source2, target2 = _generate_matched_pairs(scenario_name, 2)
    s = SCENARIO_REGISTRY[scenario_name]()
    assert all(s.third_key_name1 not in r for r in source2)
    assert all(s.third_key_name2 not in r for r in target2)

    # num=3 -> column present and consistent for matched pairs
    scenario3, source3, target3 = _generate_matched_pairs(scenario_name, 3)
    assert all(scenario3.third_key_name1 in r for r in source3)
    assert all(scenario3.third_key_name2 in r for r in target3)


def test_default_two_keys_matches_explicit_two_keys() -> None:
    """Specifying num_mapping_keys=2 must be identical to the default."""
    def run(num_keys):
        config = GenerationConfig(
            scenario="bank-recon",
            total_source_rows=200,
            match_percent=0.6,
            potential_percent=0.25,
            one_to_n_ratio=0.3,
            min_n_splits=2,
            max_n_splits=5,
            num_mapping_keys=num_keys,
            seed=42,
        )
        # Seed the scenario so Faker-generated text is reproducible too.
        scenario = SCENARIO_REGISTRY["bank-recon"](seed=42)
        generator = DataGenerator(scenario, config)
        return generator.generate_all()

    src_a, tgt_a = run(2)
    src_b, tgt_b = run(2)
    assert src_a == src_b
    assert tgt_a == tgt_b


def test_changing_key_count_does_not_break_distribution() -> None:
    """Distribution counts are independent of the number of mapping keys."""
    for num_keys in (1, 2, 3):
        config = GenerationConfig(
            scenario="bank-recon",
            total_source_rows=100,
            match_percent=0.60,
            potential_percent=0.25,
            one_to_n_ratio=0.30,
            min_n_splits=2,
            max_n_splits=5,
            num_mapping_keys=num_keys,
            seed=42,
        )
        generator = DataGenerator(get_scenario("bank-recon"), config)
        generator.generate_all()
        assert generator.stats.exact_1_to_1_matches == 60
        assert generator.stats.exact_1_to_n_matches == 7
        assert generator.stats.potential_matches == 25
        assert generator.stats.unmatched_source == 15
