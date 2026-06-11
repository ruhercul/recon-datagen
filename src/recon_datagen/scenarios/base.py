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
    
    def __init__(self, seed: int | None = None, num_mapping_keys: int = 2):
        self.faker = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)
        self._record_counter = 0
        # Number of non-monetary mapping keys to DECLARE per dataset (1-3).
        # Default 2 preserves the original composite-key behaviour.
        self.num_mapping_keys = num_mapping_keys
    
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

    # ---- Composite-key support -------------------------------------------------
    # Every scenario declares EXACTLY 2 non-monetary mapping keys + 1 monetary
    # key in its base schema (e.g. date + invoice # + amount). The number of
    # mapping keys actually DECLARED for a generation run is configurable via
    # ``num_mapping_keys`` (1-3), mirroring the get_table_keys_suggestion eval
    # distribution (1-2 typical, up to 3 for complex scenarios). Monetary keys
    # are always exactly 1.
    #
    # - num_mapping_keys == 1 -> declare only the unique reference key.
    # - num_mapping_keys == 2 -> declare both base schema keys (default).
    # - num_mapping_keys == 3 -> declare both base keys plus an extra
    #   consistently-populated allocation key column.

    # Extra (third) key column names + value pool used only when
    # ``num_mapping_keys == 3``. Distinct source/target names exercise the
    # eval's "differently named but conceptually matching" key requirement.
    third_key_name1: str = "AllocationCode"
    third_key_name2: str = "AllocationRef"
    THIRD_KEY_CATEGORIES: List[str] = [
        "ALLOC-100", "ALLOC-200", "ALLOC-300",
        "ALLOC-400", "ALLOC-500", "ALLOC-600",
    ]

    @property
    def dataset1_key_columns(self) -> List[str]:
        """Declared non-monetary key columns for dataset 1 (base schema)."""
        return [c.name for c in self.dataset1_schema if c.is_key and not c.is_monetary]

    @property
    def dataset2_key_columns(self) -> List[str]:
        """Declared non-monetary key columns for dataset 2 (base schema)."""
        return [c.name for c in self.dataset2_schema if c.is_key and not c.is_monetary]

    @property
    def dataset1_monetary_columns(self) -> List[str]:
        return [c.name for c in self.dataset1_schema if c.is_monetary]

    @property
    def dataset2_monetary_columns(self) -> List[str]:
        return [c.name for c in self.dataset2_schema if c.is_monetary]

    # ---- Effective schema (accounts for the optional third key) ----------------

    @property
    def effective_dataset1_schema(self) -> List[ColumnDef]:
        """Dataset 1 schema including the third key column when configured."""
        cols = list(self.dataset1_schema)
        if self.num_mapping_keys >= 3:
            cols.append(ColumnDef(self.third_key_name1, "string", is_key=True))
        return cols

    @property
    def effective_dataset2_schema(self) -> List[ColumnDef]:
        """Dataset 2 schema including the third key column when configured."""
        cols = list(self.dataset2_schema)
        if self.num_mapping_keys >= 3:
            cols.append(ColumnDef(self.third_key_name2, "string", is_key=True))
        return cols

    # ---- Active (declared) mapping keys ----------------------------------------

    def _active_mapping_keys(
        self, base_keys: List[str], primary_key: str, third_key: str
    ) -> List[str]:
        """Select the declared mapping keys for the configured ``num_mapping_keys``.

        - 1 key  -> the unique reference key only (``primary_key``), never the
          lower-cardinality date key, so the single declared key still uniquely
          identifies a match group.
        - 2 keys -> the base schema keys, in schema order (original behaviour).
        - 3 keys -> base schema keys plus the extra allocation key.
        """
        num = self.num_mapping_keys
        if num <= 1:
            return [primary_key]
        keys = list(base_keys)
        if num >= 3:
            keys = keys + [third_key]
        return keys[:num]

    @property
    def active_mapping_keys1(self) -> List[str]:
        """Declared mapping key columns for dataset 1 under ``num_mapping_keys``."""
        return self._active_mapping_keys(
            self.dataset1_key_columns, self.primary_key_column, self.third_key_name1
        )

    @property
    def active_mapping_keys2(self) -> List[str]:
        """Declared mapping key columns for dataset 2 under ``num_mapping_keys``."""
        return self._active_mapping_keys(
            self.dataset2_key_columns, self.secondary_key_column, self.third_key_name2
        )

    # ---- Third key population --------------------------------------------------

    @classmethod
    def _third_key_value(cls, match_group_id: str) -> str:
        """Deterministically derive the third key from the shared match id.

        Source and target of a matched group call this with the same
        ``match_group_id`` and therefore agree on the allocation key without
        any change to generation signatures.
        """
        text = str(match_group_id)
        index = sum(ord(ch) for ch in text) % len(cls.THIRD_KEY_CATEGORIES)
        return cls.THIRD_KEY_CATEGORIES[index]

    def add_third_key(
        self, record: dict, dataset: int, match_group_id: str | None = None
    ) -> dict:
        """Inject the third mapping key into a record when configured.

        For matched records (``match_group_id`` provided) the value is shared
        between source and target. For unmatched records an independent random
        value is used so they do not coincidentally form a match group.
        """
        if self.num_mapping_keys < 3:
            return record
        column = self.third_key_name1 if dataset == 1 else self.third_key_name2
        if match_group_id is not None:
            record[column] = self._third_key_value(match_group_id)
        else:
            record[column] = random.choice(self.THIRD_KEY_CATEGORIES)
        return record

    def validate_keys(self, expected_non_monetary: int = 2, expected_monetary: int = 1) -> None:
        """Ensure every dataset has exactly the expected base key counts.

        Raises ``ValueError`` if any dataset deviates from
        ``expected_non_monetary`` non-monetary keys or ``expected_monetary``
        monetary keys. This validates the scenario's *base* schema shape; the
        number of keys actually declared at generation time is controlled by
        ``num_mapping_keys``.
        """
        checks = [
            ("dataset1", self.dataset1_name, self.dataset1_key_columns, self.dataset1_monetary_columns),
            ("dataset2", self.dataset2_name, self.dataset2_key_columns, self.dataset2_monetary_columns),
        ]
        errors = []
        for label, ds_name, non_monetary, monetary in checks:
            if len(non_monetary) != expected_non_monetary:
                errors.append(
                    f"Scenario '{self.name}' {label} ({ds_name}) has "
                    f"{len(non_monetary)} non-monetary key(s) {non_monetary}; "
                    f"need exactly {expected_non_monetary}."
                )
            if len(monetary) != expected_monetary:
                errors.append(
                    f"Scenario '{self.name}' {label} ({ds_name}) has "
                    f"{len(monetary)} monetary column(s) {monetary}; "
                    f"need exactly {expected_monetary}."
                )
        if errors:
            raise ValueError(" ".join(errors))

    
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

    @staticmethod
    def _skip_non_alphanumeric_chars(text: str, start_index: int) -> int:
        """Skip punctuation the same way Finance.Copilot partial matching does."""
        current_index = start_index
        while current_index < len(text) and not text[current_index].isalnum():
            current_index += 1

        return current_index

    @classmethod
    def _is_alphanumeric_match_from(
        cls,
        primary_value: str,
        secondary_value: str,
        primary_start_index: int,
        secondary_start_index: int,
    ) -> bool:
        primary_index = primary_start_index
        secondary_index = secondary_start_index

        while primary_index < len(primary_value) and secondary_index < len(secondary_value):
            if not secondary_value[secondary_index].isalnum() and not secondary_value[secondary_index].isspace():
                secondary_index = cls._skip_non_alphanumeric_chars(secondary_value, secondary_index)

            if secondary_index == len(secondary_value):
                break

            if not primary_value[primary_index].isalnum() and not primary_value[primary_index].isspace():
                primary_index = cls._skip_non_alphanumeric_chars(primary_value, primary_index)

            if primary_index == len(primary_value):
                break

            if primary_value[primary_index].lower() != secondary_value[secondary_index].lower():
                return False

            primary_index += 1
            secondary_index += 1

        secondary_index = cls._skip_non_alphanumeric_chars(secondary_value, secondary_index)

        if secondary_index != len(secondary_value):
            return False

        return primary_index == len(primary_value) or not primary_value[primary_index].isalnum()

    @classmethod
    def is_partial_match(cls, primary_value: str, secondary_value: str) -> bool:
        """Mirror Finance.Copilot ReconciliationPartialMatchUtilities.IsPartialMatch."""
        if not primary_value and not secondary_value:
            return True

        primary_index = 0
        secondary_index = 0

        while primary_index < len(primary_value) and secondary_index < len(secondary_value):
            primary_index = cls._skip_non_alphanumeric_chars(primary_value, primary_index)
            secondary_index = cls._skip_non_alphanumeric_chars(secondary_value, secondary_index)

            if primary_index == len(primary_value) or secondary_index == len(secondary_value):
                break

            if primary_value[primary_index].lower() == secondary_value[secondary_index].lower():
                matched = cls._is_alphanumeric_match_from(
                    primary_value,
                    secondary_value,
                    primary_index,
                    secondary_index,
                )
                if matched:
                    return True

            while primary_index < len(primary_value) and primary_value[primary_index].isalnum():
                primary_index += 1

        return False

    def _make_partial_secondary_key(self, reference: str) -> str:
        """Create a target key that Finance.Copilot will match as partial."""
        reference = str(reference)
        candidates = []

        if "-" in reference:
            parts = reference.split("-")
            if len(parts) > 2:
                candidates.append("-".join(parts[1:]))
                candidates.append("-".join(parts[:-1]))

        alphanumeric = "".join(character for character in reference if character.isalnum())
        if alphanumeric:
            candidates.append(alphanumeric)

        digits = "".join(character for character in reference if character.isdigit())
        if digits:
            candidates.append(digits)

        valid_candidates = [
            candidate
            for candidate in candidates
            if candidate and candidate != reference and self.is_partial_match(reference, candidate)
        ]

        return random.choice(valid_candidates) if valid_candidates else reference
    
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
        
        elif variance_type == VarianceType.TOLERANCE_AMOUNT:
            # Finance.Copilot: same mapping keys, amount within tolerance.
            # Keys stay identical; only the monetary amount is modified by a
            # small value within the tolerance range.
            if self.secondary_monetary_column in modified:
                original = modified[self.secondary_monetary_column]
                # Always produce a non-zero difference so it isn't exact
                sign = random.choice([-1, 1])
                variance = original * random.uniform(
                    amount_variance_percent * 0.1,
                    amount_variance_percent,
                )
                adjusted_amount = round(
                    original + sign * variance, 2
                )
                if adjusted_amount == original and amount_variance_percent > 0:
                    adjusted_amount = round(original + sign * 0.01, 2)

                modified[self.secondary_monetary_column] = adjusted_amount

        elif variance_type == VarianceType.PARTIAL_MATCH_AMOUNT_EQUAL:
            # Finance.Copilot IsPartialMatch(primary, secondary) checks whether
            # secondary's alphanumeric content appears as a contiguous, word-
            # boundary-aligned substring inside primary.  Therefore the TARGET
            # (secondary) must be SHORTER / a subset of the source (primary).
            # Amounts stay EQUAL -> classified as "Potentially Matched".
            if self.secondary_key_column in modified:
                ref = str(modified[self.secondary_key_column])
                modified[self.secondary_key_column] = self._make_partial_secondary_key(ref)
            # Note: Amount is NOT modified - stays equal for potential match classification
        
        elif variance_type == VarianceType.PARTIAL_MATCH_AMOUNT_DIFF:
            # Finance.Copilot: partial key match (secondary subset of primary)
            # + amount difference → classified as "Unmatched".
            # Use same subset-style key mutations as PARTIAL_MATCH_AMOUNT_EQUAL.
            if self.secondary_key_column in modified:
                ref = str(modified[self.secondary_key_column])
                modified[self.secondary_key_column] = self._make_partial_secondary_key(ref)

            # Also modify the amount - this creates the unmatched classification
            if self.secondary_monetary_column in modified:
                original = modified[self.secondary_monetary_column]
                sign = random.choice([-1, 1])
                variance = original * random.uniform(
                    amount_variance_percent, amount_variance_percent * 3,
                )
                adjusted_amount = round(
                    original + sign * variance, 2
                )
                if adjusted_amount == original:
                    adjusted_amount = round(original + sign * 0.01, 2)

                modified[self.secondary_monetary_column] = adjusted_amount
        
        return modified
    
    def get_dataset1_columns(self) -> List[str]:
        """Get column names for dataset 1 (includes the third key when configured)."""
        return [col.name for col in self.effective_dataset1_schema]
    
    def get_dataset2_columns(self) -> List[str]:
        """Get column names for dataset 2 (includes the third key when configured)."""
        return [col.name for col in self.effective_dataset2_schema]
