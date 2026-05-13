from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recon_datagen.generator import DataGenerator
from recon_datagen.models import GenerationConfig
from recon_datagen.scenarios import get_scenario
from recon_datagen.scenarios.base import ReconciliationScenario


@pytest.mark.parametrize(
    ("primary_value", "secondary_value", "expected"),
    [
        ("test", "test", True),
        ("test 123 456", "test 123", True),
        ("Inv Xyz 123", "Xyz 123", True),
        ("Inv xyz 123 test data", "Xyz", True),
        ("Misc. Test", "'Misc'", True),
        ("C4F Demo-Flights", "flights", True),
        ("Invoice \"INV123456\" Date: 2/26/2024", "INV123456", True),
        ("test", "test1", False),
        ("Inv1234a", "Inv1234", False),
        ("Inv12345", "Inv1234", False),
        ("Inv-94fa45a", "Inv-94fa45", False),
        ("test-1", "!", False),
        ("This isCopilotDemo", "CoPilot", False),
        ("12test123", "123 test data", False),
        ("Inv 123", "Inv10005", False),
        ("Inv#123", "Inv#1234", False),
        ("Inv#1234", "nv#01234", False),
        ("Inv#01234", "Inv#1234", False),
        ("Invoice \"INV123456\" Date: 2/26/2024", "INV1234567", False),
    ],
)
def test_partial_match_matches_core_examples(primary_value, secondary_value, expected):
    assert ReconciliationScenario.is_partial_match(primary_value, secondary_value) is expected


def test_distribution_uses_core_classification_buckets():
    config = GenerationConfig(
        scenario="bank-recon",
        total_source_rows=100,
        match_percent=0.60,
        potential_percent=0.25,
        one_to_n_ratio=0.30,
        min_n_splits=2,
        max_n_splits=5,
        seed=42,
    )
    scenario = get_scenario("bank-recon")
    generator = DataGenerator(scenario, config)

    generator.generate_all()

    assert generator.stats.exact_1_to_1_matches == 60
    assert generator.stats.exact_1_to_n_matches == 7
    assert generator.stats.potential_matches == 25
    assert generator.stats.unmatched_source == 15


def test_one_to_n_uses_same_key_and_counts_as_potential():
    config = GenerationConfig(
        scenario="bank-recon",
        total_source_rows=20,
        match_percent=0,
        potential_percent=1,
        one_to_n_ratio=1,
        min_n_splits=3,
        max_n_splits=3,
        seed=7,
    )
    scenario = get_scenario("bank-recon")
    generator = DataGenerator(scenario, config)

    generator.generate_all()

    source_record = generator.stats.example_1_to_n_source
    target_records = generator.stats.example_1_to_n_targets

    assert source_record is not None
    assert target_records is not None
    assert generator.stats.exact_1_to_n_matches == 20
    assert generator.stats.potential_matches == 20
    assert {target_record["BankReference"] for target_record in target_records} == {source_record["DocumentNumber"]}
    assert round(sum(target_record["BankAmount"] for target_record in target_records), 2) == source_record["Amount"]


def test_partial_potential_example_is_valid_partial_match():
    config = GenerationConfig(
        scenario="bank-recon",
        total_source_rows=10,
        match_percent=0,
        potential_percent=1,
        one_to_n_ratio=0,
        amount_variance_percent=0,
        seed=11,
    )
    scenario = get_scenario("bank-recon")
    generator = DataGenerator(scenario, config)

    generator.generate_all()

    source_record = generator.stats.example_partial_match_source
    target_record = generator.stats.example_partial_match_target

    assert source_record is not None
    assert target_record is not None
    assert source_record["DocumentNumber"] != target_record["BankReference"]
    assert scenario.is_partial_match(source_record["DocumentNumber"], target_record["BankReference"])
    assert source_record["Amount"] == target_record["BankAmount"]


def test_generated_match_group_ids_are_unique_for_large_runs():
    config = GenerationConfig(
        scenario="bank-recon",
        total_source_rows=5000,
        match_percent=0.70,
        potential_percent=0.20,
        one_to_n_ratio=0.25,
        seed=123,
    )
    scenario = get_scenario("bank-recon")
    generator = DataGenerator(scenario, config)

    source_records, target_records = generator.generate_all()
    assert target_records

    generated_group_keys = [
        source_record["DocumentNumber"]
        for source_record in source_records
        if str(source_record["DocumentNumber"]).startswith("REF-")
    ]

    assert len(generated_group_keys) == len(set(generated_group_keys))