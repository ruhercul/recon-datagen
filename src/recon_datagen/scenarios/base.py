"""Base class for reconciliation scenarios."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple
from faker import Faker
import random
from datetime import date, timedelta

from ..models import ColumnDef, VarianceType


@dataclass
class MatchGroup:
    """Represents a group of matched records."""
    group_id: str
    source_record: dict
    target_records: list[dict]


class ReconciliationScenario(ABC):
    """Abstract base class for reconciliation scenarios.
    
    Each scenario defines:
    - The schema for both datasets
    - How to generate matching/non-matching records
    - The matching keys (including monetary key)
    """
    
    def __init__(self, seed: int | None = None):
        self.faker = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)
        self._record_counter = 0
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this scenario."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for this scenario."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this scenario represents."""
        pass
    
    @property
    @abstractmethod
    def dataset1_name(self) -> str:
        """Name of the first dataset (source)."""
        pass
    
    @property
    @abstractmethod
    def dataset2_name(self) -> str:
        """Name of the second dataset (target)."""
        pass
    
    @property
    @abstractmethod
    def dataset1_schema(self) -> List[ColumnDef]:
        """Schema definition for dataset 1."""
        pass
    
    @property
    @abstractmethod
    def dataset2_schema(self) -> List[ColumnDef]:
        """Schema definition for dataset 2."""
        pass
    
    @property
    @abstractmethod
    def primary_key_column(self) -> str:
        """The primary matching key column name in dataset1 (source)."""
        pass
    
    @property
    @abstractmethod
    def secondary_key_column(self) -> str:
        """The secondary matching key column name in dataset2 (target)."""
        pass
    
    @property
    @abstractmethod
    def monetary_key_column(self) -> str:
        """The monetary key column name in dataset1 (source)."""
        pass
    
    @property
    @abstractmethod
    def secondary_monetary_column(self) -> str:
        """The monetary key column name in dataset2 (target)."""
        pass
    
    def _generate_unique_id(self, prefix: str = "") -> str:
        """Generate a unique ID for records."""
        self._record_counter += 1
        return f"{prefix}{self._record_counter:08d}"
    
    def _generate_reference_id(self) -> str:
        """Generate a realistic reference/transaction ID."""
        prefix = random.choice(["TXN", "REF", "DOC", "INV", "PO", "PAY"])
        year = random.randint(2023, 2025)
        sequence = random.randint(100000, 999999)
        return f"{prefix}-{year}-{sequence}"
    
    def _generate_amount(self, min_val: float = 100, max_val: float = 100000) -> float:
        """Generate a random monetary amount."""
        return round(random.uniform(min_val, max_val), 2)
    
    def _generate_date(self, start_days_ago: int = 365, end_days_ago: int = 0) -> date:
        """Generate a random date within range."""
        start_date = date.today() - timedelta(days=start_days_ago)
        end_date = date.today() - timedelta(days=end_days_ago)
        days_between = (end_date - start_date).days
        random_days = random.randint(0, max(0, days_between))
        return start_date + timedelta(days=random_days)
    
    def _split_amount(self, total: float, n_parts: int) -> List[float]:
        """Split an amount into n parts that sum to the total."""
        if n_parts <= 0:
            return []
        if n_parts == 1:
            return [total]
        
        # Generate random split points
        splits = sorted([random.random() for _ in range(n_parts - 1)])
        splits = [0] + splits + [1]
        
        # Calculate amounts from split points
        amounts = []
        for i in range(n_parts):
            proportion = splits[i + 1] - splits[i]
            amount = round(total * proportion, 2)
            amounts.append(amount)
        
        # Adjust for rounding errors
        diff = round(total - sum(amounts), 2)
        if diff != 0 and amounts:
            amounts[-1] = round(amounts[-1] + diff, 2)
        
        return amounts
    
    @abstractmethod
    def generate_source_record(
        self, 
        match_group_id: str, 
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate a single source (dataset1) record."""
        pass
    
    @abstractmethod
    def generate_target_records(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date,
        split_count: int = 1,
        exact_match: bool = True
    ) -> List[dict]:
        """Generate target (dataset2) records for a match.
        
        For 1:1 matches, split_count=1.
        For 1:N matches, split_count>1 and amounts should sum to total.
        
        Args:
            match_group_id: The shared reference/key between source and target
            amount: The monetary amount (will be split if split_count > 1)
            transaction_date: The transaction date from source record
            split_count: Number of target records to generate (1 for 1:1, >1 for 1:N)
            exact_match: If True, all matching keys (dates, amounts, references) must match exactly.
                        If False, small variances may be introduced for potential matches.
        """
        pass
    
    @abstractmethod
    def generate_unmatched_source_record(self) -> dict:
        """Generate a source record with no match."""
        pass
    
    @abstractmethod
    def generate_unmatched_target_record(self) -> dict:
        """Generate a target record with no match."""
        pass
    
    def apply_variance(
        self, 
        record: dict, 
        variance_type: VarianceType,
        amount_variance_percent: float = 0.05,
        date_variance_days: int = 3
    ) -> dict:
        """Apply variance to create a potential match.
        
        This is applied to TARGET records, so we use secondary_key_column
        and secondary_monetary_column (target column names).
        
        Returns a modified copy of the record.
        """
        modified = record.copy()
        
        if variance_type == VarianceType.AMOUNT_DIFFERENCE:
            # Use target's monetary column
            if self.secondary_monetary_column in modified:
                original = modified[self.secondary_monetary_column]
                variance = original * random.uniform(-amount_variance_percent, amount_variance_percent)
                modified[self.secondary_monetary_column] = round(original + variance, 2)
        
        elif variance_type == VarianceType.DATE_DIFFERENCE:
            # Find date columns and adjust them
            for key, value in modified.items():
                if isinstance(value, date) and 'date' in key.lower():
                    days_off = random.randint(-date_variance_days, date_variance_days)
                    modified[key] = value + timedelta(days=days_off)
                    break
        
        elif variance_type == VarianceType.REFERENCE_TYPO:
            # Use target's key column
            if self.secondary_key_column in modified:
                ref = modified[self.secondary_key_column]
                if len(ref) > 3:
                    # Introduce a typo (swap characters, wrong digit, etc.)
                    typo_type = random.choice(['swap', 'replace', 'truncate'])
                    if typo_type == 'swap' and len(ref) > 4:
                        i = random.randint(1, len(ref) - 3)
                        ref = ref[:i] + ref[i+1] + ref[i] + ref[i+2:]
                    elif typo_type == 'replace':
                        i = random.randint(0, len(ref) - 1)
                        if ref[i].isdigit():
                            new_char = str((int(ref[i]) + 1) % 10)
                        else:
                            new_char = chr((ord(ref[i]) - ord('A') + 1) % 26 + ord('A'))
                        ref = ref[:i] + new_char + ref[i+1:]
                    elif typo_type == 'truncate':
                        ref = ref[:-1]
                    modified[self.secondary_key_column] = ref
        
        elif variance_type == VarianceType.PARTIAL_MATCH_AMOUNT_EQUAL:
            # Per MS Copilot Finance: substring matching on mapping key
            # Target reference becomes a superset (contains source ref) or subset
            # Amounts stay EQUAL -> classified as "Potentially Matched"
            # Use target's key column
            if self.secondary_key_column in modified:
                ref = modified[self.secondary_key_column]
                partial_type = random.choice(['superset', 'subset', 'prefix_add', 'suffix_add'])
                
                if partial_type == 'superset':
                    # Add suffix to make target a superset of source
                    suffix = f"-{random.randint(1,99):02d}"
                    ref = ref + suffix
                elif partial_type == 'subset':
                    # Remove part of reference (target is substring of source)
                    if '-' in ref:
                        parts = ref.split('-')
                        if len(parts) > 2:
                            ref = '-'.join(parts[1:])  # Remove first part
                elif partial_type == 'prefix_add':
                    # Add prefix
                    prefix = random.choice(['PMT-', 'TRF-', 'ACH-', 'WIR-'])
                    ref = prefix + ref
                elif partial_type == 'suffix_add':
                    # Add descriptive suffix
                    suffix = random.choice(['-A', '-B', '-PART1', '-SPLIT'])
                    ref = ref + suffix
                
                modified[self.secondary_key_column] = ref
            # Note: Amount is NOT modified - stays equal for potential match classification
        
        elif variance_type == VarianceType.PARTIAL_MATCH_AMOUNT_DIFF:
            # Per MS Copilot Finance: partial key match + amount difference
            # This should be classified as "Unmatched" per the documentation
            # Use target's key column
            if self.secondary_key_column in modified:
                ref = modified[self.secondary_key_column]
                partial_type = random.choice(['superset', 'subset', 'prefix_add', 'suffix_add'])
                
                if partial_type == 'superset':
                    suffix = f"-{random.randint(1,99):02d}"
                    ref = ref + suffix
                elif partial_type == 'subset':
                    if '-' in ref:
                        parts = ref.split('-')
                        if len(parts) > 2:
                            ref = '-'.join(parts[1:])
                elif partial_type == 'prefix_add':
                    prefix = random.choice(['PMT-', 'TRF-', 'ACH-', 'WIR-'])
                    ref = prefix + ref
                elif partial_type == 'suffix_add':
                    suffix = random.choice(['-A', '-B', '-PART1', '-SPLIT'])
                    ref = ref + suffix
                
                modified[self.secondary_key_column] = ref
            
            # Also modify the amount - this creates the unmatched classification
            # Use target's monetary column
            if self.secondary_monetary_column in modified:
                original = modified[self.secondary_monetary_column]
                variance = original * random.uniform(-amount_variance_percent, amount_variance_percent)
                modified[self.secondary_monetary_column] = round(original + variance, 2)
        
        return modified
    
    def get_dataset1_columns(self) -> List[str]:
        """Get column names for dataset 1."""
        return [col.name for col in self.dataset1_schema]
    
    def get_dataset2_columns(self) -> List[str]:
        """Get column names for dataset 2."""
        return [col.name for col in self.dataset2_schema]
