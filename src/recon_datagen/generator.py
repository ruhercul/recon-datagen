"""Core data generation engine."""

import random
from typing import Generator
from datetime import date

from .models import GenerationConfig, GenerationStats, MatchType, VarianceType
from .scenarios.base import ReconciliationScenario


class DataGenerator:
    """Generates reconciliation test data based on configuration.
    
    Produces matched, potentially matched, and unmatched records
    according to the specified distribution percentages.
    """
    
    def __init__(self, scenario: ReconciliationScenario, config: GenerationConfig):
        self.scenario = scenario
        self.config = config
        self.stats = GenerationStats()
        self._match_group_counter = 0
        
        # Set random seed for reproducibility
        if config.seed is not None:
            random.seed(config.seed)
    
    def _calculate_distribution(self) -> dict[MatchType, int]:
        """Calculate how many records of each type to generate."""
        total = self.config.total_source_rows
        
        # Finance.Copilot only reports exact 1:1 groups as Matched. Same-key
        # multi-row aggregate groups are reported as PotentiallyMatched.
        exact_match_count = int(total * self.config.match_percent)
        potential_count = int(total * self.config.potential_percent)
        unmatched_source_count = total - exact_match_count - potential_count
        
        # Within potential matches, split out the 1:N aggregate cases.
        one_to_n_count = int(potential_count * self.config.one_to_n_ratio)
        near_match_count = potential_count - one_to_n_count
        
        # Also generate some unmatched target records (orphans in dataset2)
        unmatched_target_count = int(unmatched_source_count * 0.5)  # Half as many orphan targets
        
        return {
            MatchType.EXACT_1_TO_1: exact_match_count,
            MatchType.EXACT_1_TO_N: one_to_n_count,
            MatchType.POTENTIAL: near_match_count,
            MatchType.UNMATCHED_SOURCE: unmatched_source_count,
            MatchType.UNMATCHED_TARGET: unmatched_target_count,
        }
    
    def _generate_match_group_id(self, prefix: str = "REF") -> str:
        """Generate a unique match group ID."""
        self._match_group_counter += 1
        year = random.randint(2023, 2025)
        sequence = self._match_group_counter
        return f"{prefix}-{year}-{sequence}"
    
    def generate(self) -> Generator[tuple[list[dict], list[dict]], None, None]:
        """Generate data in chunks.
        
        Yields tuples of (source_records, target_records) for each chunk.
        """
        distribution = self._calculate_distribution()
        
        # Create a shuffled list of match types to generate
        match_types = []
        for match_type, count in distribution.items():
            match_types.extend([match_type] * count)
        random.shuffle(match_types)
        
        # Process in chunks
        chunk_size = self.config.chunk_size
        source_chunk = []
        target_chunk = []
        
        for match_type in match_types:
            source_records, target_records = self._generate_record_pair(match_type)
            source_chunk.extend(source_records)
            target_chunk.extend(target_records)
            
            # Yield chunk when it's full
            if len(source_chunk) >= chunk_size:
                yield source_chunk, target_chunk
                source_chunk = []
                target_chunk = []
        
        # Yield any remaining records
        if source_chunk or target_chunk:
            yield source_chunk, target_chunk
    
    def _generate_record_pair(
        self, 
        match_type: MatchType
    ) -> tuple[list[dict], list[dict]]:
        """Generate a pair of source and target records based on match type."""
        source_records = []
        target_records = []
        
        if match_type == MatchType.EXACT_1_TO_1:
            match_group_id = self._generate_match_group_id()
            amount = self.scenario._generate_amount()
            txn_date = self.scenario._generate_date()
            
            source_record = self.scenario.generate_source_record(
                match_group_id, amount, txn_date
            )
            target_record_list = self.scenario.generate_target_records(
                match_group_id, amount, txn_date, split_count=1, exact_match=True
            )
            
            source_records.append(source_record)
            target_records.extend(target_record_list)
            
            # Store first 1:1 example for verification
            if self.stats.example_1_to_1_source is None:
                self.stats.example_1_to_1_source = source_record.copy()
                self.stats.example_1_to_1_target = target_record_list[0].copy()
            
            self.stats.exact_1_to_1_matches += 1
            self.stats.source_rows += 1
            self.stats.target_rows += len(target_record_list)
        
        elif match_type == MatchType.EXACT_1_TO_N:
            match_group_id = self._generate_match_group_id()
            amount = self.scenario._generate_amount()
            txn_date = self.scenario._generate_date()
            
            # Determine number of splits
            n_splits = random.randint(
                self.config.min_n_splits, 
                self.config.max_n_splits
            )
            
            source_record = self.scenario.generate_source_record(
                match_group_id, amount, txn_date
            )
            target_record_list = self.scenario.generate_target_records(
                match_group_id, amount, txn_date, split_count=n_splits, exact_match=True
            )
            
            source_records.append(source_record)
            target_records.extend(target_record_list)
            
            # Store first 1:N example for verification
            if self.stats.example_1_to_n_source is None:
                self.stats.example_1_to_n_source = source_record.copy()
                self.stats.example_1_to_n_targets = [t.copy() for t in target_record_list]
            
            self.stats.exact_1_to_n_matches += 1
            self.stats.potential_matches += 1
            self.stats.source_rows += 1
            self.stats.target_rows += len(target_record_list)
        
        elif match_type == MatchType.POTENTIAL:
            match_group_id = self._generate_match_group_id()
            amount = self.scenario._generate_amount()
            txn_date = self.scenario._generate_date()
            
            # Finance.Copilot classifies single-row near matches as
            # PotentiallyMatched when either amount tolerance or partial key
            # matching is configured. Avoid tolerance-only records when the
            # configured amount variance is zero because those become exact
            # Matched rows in the core engine.
            potential_styles = ["partial_key"]
            potential_weights = [40]
            if self.config.amount_variance_percent > 0:
                potential_styles.append("tolerance")
                potential_weights.append(60)

            potential_style = random.choices(
                potential_styles,
                weights=potential_weights,
                k=1,
            )[0]
            
            if potential_style == "tolerance":
                # Case 1 – Same mapping keys, amount within tolerance.
                # Keys match exactly; only the monetary amount differs by a
                # small value within the configured tolerance range.
                source_record = self.scenario.generate_source_record(
                    match_group_id, amount, txn_date
                )
                target_record_list = self.scenario.generate_target_records(
                    match_group_id, amount, txn_date,
                    split_count=1, exact_match=True,
                )
                target_record_list = [
                    self.scenario.apply_variance(
                        record,
                        VarianceType.TOLERANCE_AMOUNT,
                        self.config.amount_variance_percent,
                        self.config.date_variance_days,
                    )
                    for record in target_record_list
                ]
            else:
                # Case 3 – Partial key match + amounts equal.
                # The secondary key is a proper substring/subset of the
                # primary key (aligns with Finance.Copilot's IsPartialMatch
                # algorithm).  Amounts stay identical.
                source_record = self.scenario.generate_source_record(
                    match_group_id, amount, txn_date
                )
                target_record_list = self.scenario.generate_target_records(
                    match_group_id, amount, txn_date,
                    split_count=1, exact_match=True,
                )
                target_record_list = [
                    self.scenario.apply_variance(
                        record,
                        VarianceType.PARTIAL_MATCH_AMOUNT_EQUAL,
                        self.config.amount_variance_percent,
                        self.config.date_variance_days,
                    )
                    for record in target_record_list
                ]
            
            source_records.append(source_record)
            target_records.extend(target_record_list)
            
            # Store first partial-match example for verification
            if potential_style == "partial_key" and self.stats.example_partial_match_source is None:
                self.stats.example_partial_match_source = source_record.copy()
                self.stats.example_partial_match_target = target_record_list[0].copy()
            
            self.stats.potential_matches += 1
            self.stats.source_rows += 1
            self.stats.target_rows += len(target_record_list)
        
        elif match_type == MatchType.UNMATCHED_SOURCE:
            source_record = self.scenario.generate_unmatched_source_record()
            source_records.append(source_record)
            
            self.stats.unmatched_source += 1
            self.stats.source_rows += 1
        
        elif match_type == MatchType.UNMATCHED_TARGET:
            target_record = self.scenario.generate_unmatched_target_record()
            target_records.append(target_record)
            
            self.stats.unmatched_target += 1
            self.stats.target_rows += 1
        
        return source_records, target_records
    
    def generate_all(self) -> tuple[list[dict], list[dict]]:
        """Generate all data at once (for smaller datasets).
        
        Returns tuple of (all_source_records, all_target_records).
        """
        all_source = []
        all_target = []
        
        for source_chunk, target_chunk in self.generate():
            all_source.extend(source_chunk)
            all_target.extend(target_chunk)
        
        # Shuffle to mix up the order
        random.shuffle(all_source)
        random.shuffle(all_target)
        
        return all_source, all_target
