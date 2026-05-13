"""Data models and schemas for reconciliation data generation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class MatchType(Enum):
    """Types of matches between datasets."""
    EXACT_1_TO_1 = "exact_1_to_1"
    # Same-key multi-row groups are aggregate matches, but Finance.Copilot
    # reports them as PotentiallyMatched rather than Matched.
    EXACT_1_TO_N = "exact_1_to_n"
    POTENTIAL = "potential"
    UNMATCHED_SOURCE = "unmatched_source"
    UNMATCHED_TARGET = "unmatched_target"


class VarianceType(Enum):
    """Types of variances for potential matches."""
    AMOUNT_DIFFERENCE = "amount_difference"
    DATE_DIFFERENCE = "date_difference"
    REFERENCE_TYPO = "reference_typo"
    # Finance.Copilot "Potentially Matched" categories:
    #
    # 1. TOLERANCE_AMOUNT: Same mapping keys, amounts differ within tolerance.
    #    This is the most common Potentially Matched case.
    TOLERANCE_AMOUNT = "tolerance_amount"
    # 2. Partial matching (via IsPartialMatch algorithm):
    #    - The algorithm checks if secondary's alphanumeric content appears
    #      as a contiguous word-boundary-aligned substring inside primary.
    #    - Therefore secondary must be shorter/subset of primary.
    #    - PARTIAL_MATCH_AMOUNT_EQUAL: partial key + same amount -> Potentially Matched
    #    - PARTIAL_MATCH_AMOUNT_DIFF: partial key + different amount -> Unmatched
    PARTIAL_MATCH_AMOUNT_EQUAL = "partial_match_amount_equal"
    PARTIAL_MATCH_AMOUNT_DIFF = "partial_match_amount_diff"


@dataclass
class ColumnDef:
    """Definition of a column in a dataset."""
    name: str
    data_type: str  # 'string', 'decimal', 'integer', 'date', 'datetime'
    is_key: bool = False
    is_monetary: bool = False
    nullable: bool = False
    description: str = ""


@dataclass
class GenerationConfig:
    """Configuration for data generation."""
    scenario: str
    total_source_rows: int
    match_percent: float  # Strict Finance.Copilot Matched rows: exact 1:1 only
    potential_percent: float  # Finance.Copilot PotentiallyMatched rows
    # unmatched = 1.0 - match_percent - potential_percent
    
    one_to_n_ratio: float = 0.3  # Within potential matches, % that are 1:N aggregate groups
    min_n_splits: int = 2
    max_n_splits: int = 5
    
    # Variance settings for potential matches
    amount_variance_percent: float = 0.05  # ±5% for potential matches
    date_variance_days: int = 3
    
    # Output settings
    output_path: str = "reconciliation_test_data.xlsx"
    seed: Optional[int] = None
    
    # Chunk size for large file generation
    chunk_size: int = 10000
    
    @property
    def unmatched_percent(self) -> float:
        """Calculate unmatched percentage."""
        return max(0.0, 1.0 - self.match_percent - self.potential_percent)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if self.total_source_rows < 1:
            errors.append("Total rows must be at least 1")
        
        if not 0 <= self.match_percent <= 1:
            errors.append("Match percent must be between 0 and 1")
        
        if not 0 <= self.potential_percent <= 1:
            errors.append("Potential percent must be between 0 and 1")
        
        if self.match_percent + self.potential_percent > 1:
            errors.append("Match + Potential percent cannot exceed 100%")
        
        if not 0 <= self.one_to_n_ratio <= 1:
            errors.append("1:N ratio must be between 0 and 1")
        
        if self.min_n_splits < 2:
            errors.append("Minimum splits must be at least 2")
        
        if self.max_n_splits < self.min_n_splits:
            errors.append("Maximum splits must be >= minimum splits")
        
        return errors


@dataclass
class GenerationStats:
    """Statistics from data generation."""
    source_rows: int = 0
    target_rows: int = 0
    exact_1_to_1_matches: int = 0
    exact_1_to_n_matches: int = 0
    potential_matches: int = 0
    unmatched_source: int = 0
    unmatched_target: int = 0
    
    # Example records for verification
    example_1_to_1_source: Optional[dict] = None
    example_1_to_1_target: Optional[dict] = None
    example_1_to_n_source: Optional[dict] = None
    example_1_to_n_targets: Optional[List[dict]] = None
    # Partial match example (Finance.Copilot IsPartialMatch semantics)
    example_partial_match_source: Optional[dict] = None
    example_partial_match_target: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """Convert stats to dictionary."""
        non_multi_row_potential = max(
            0,
            self.potential_matches - self.exact_1_to_n_matches,
        )

        return {
            "Source Dataset Rows": self.source_rows,
            "Target Dataset Rows": self.target_rows,
            "Matched (Exact 1:1)": self.exact_1_to_1_matches,
            "Potentially Matched (Total)": self.potential_matches,
            "  - Potential 1:N Aggregate": self.exact_1_to_n_matches,
            "  - Potential Tolerance/Partial": non_multi_row_potential,
            "Unmatched (Source Only)": self.unmatched_source,
            "Unmatched (Target Only)": self.unmatched_target,
        }
