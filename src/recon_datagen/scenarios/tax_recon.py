"""Tax Reconciliation scenario - ERP Tax Calculation vs Filed Tax Return."""

from datetime import date, timedelta
from typing import List
import random

from .base import ReconciliationScenario
from ..models import ColumnDef


class TaxReconciliationScenario(ReconciliationScenario):
    """Tax reconciliation: ERP Tax Calculation vs Filed Tax Return.
    
    Dataset 1 (Source): ERP Tax Calculation
    Dataset 2 (Target): Filed Tax Return
    
    Common scenarios:
    - 1:1: Single ERP calculation matches single return line
    - 1:N: Single calculation split across multiple return schedules
    - Potential: Calculation differences, adjustment entries
    """
    
    @property
    def name(self) -> str:
        return "tax-recon"
    
    @property
    def display_name(self) -> str:
        return "Tax Reconciliation"
    
    @property
    def description(self) -> str:
        return "Reconcile ERP Tax Calculations against Filed Tax Returns"
    
    @property
    def dataset1_name(self) -> str:
        return "ERP_Tax_Calculation"
    
    @property
    def dataset2_name(self) -> str:
        return "Filed_Tax_Return"
    
    @property
    def dataset1_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("TaxType", "string"),
            ColumnDef("Jurisdiction", "string", is_key=True),  # Composite key: jurisdiction + filing period
            ColumnDef("FilingPeriod", "string", is_key=True),  # Composite key: jurisdiction + filing period
            ColumnDef("TransactionCount", "integer"),
            ColumnDef("TaxableBase", "decimal"),
            ColumnDef("CalculatedTax", "decimal", is_monetary=True),
            ColumnDef("Adjustments", "decimal"),
            ColumnDef("EntityID", "string"),
        ]
    
    @property
    def dataset2_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("TaxReturnID", "string"),  # Unique identifier
            ColumnDef("TaxType", "string"),
            ColumnDef("Jurisdiction", "string", is_key=True),  # Composite key: jurisdiction + filing period
            ColumnDef("FilingPeriod", "string", is_key=True),  # Composite key: jurisdiction + filing period
            ColumnDef("ReportedTax", "decimal", is_monetary=True),
            ColumnDef("PaymentsMade", "decimal"),
            ColumnDef("Refunds", "decimal"),
            ColumnDef("EntityID", "string"),
        ]
    
    @property
    def primary_key_column(self) -> str:
        return "FilingPeriod"
    
    @property
    def monetary_key_column(self) -> str:
        return "CalculatedTax"
    
    @property
    def secondary_key_column(self) -> str:
        return "FilingPeriod"
    
    @property
    def secondary_monetary_column(self) -> str:
        return "ReportedTax"
    
    def _get_tax_type(self) -> str:
        """Get a tax type."""
        return random.choice(["SALES", "VAT", "GST", "INCOME", "PAYROLL", "EXCISE", "PROPERTY"])
    
    def _get_jurisdiction(self) -> str:
        """Get a tax jurisdiction."""
        return random.choice([
            "US-FED", "US-CA", "US-NY", "US-TX", "US-FL",
            "UK", "DE", "FR", "JP", "AU", "CA-FED", "CA-ON"
        ])
    
    def _get_filing_period(self, txn_date: date) -> str:
        """Get filing period."""
        # Quarterly filing
        quarter = (txn_date.month - 1) // 3 + 1
        return f"{txn_date.year}-Q{quarter}"
    
    def _get_entity_id(self) -> str:
        """Get an entity ID."""
        return f"ENT{random.randint(100, 999)}"
    
    def generate_source_record(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate an ERP Tax Calculation record."""
        taxable_base = round(abs(amount) / random.uniform(0.05, 0.25), 2)
        adjustments = round(random.uniform(-1000, 1000), 2) if random.random() < 0.2 else 0
        
        return {
            "TaxType": self._get_tax_type(),
            "Jurisdiction": self._get_jurisdiction(),
            "FilingPeriod": match_group_id,
            "TransactionCount": random.randint(100, 10000),
            "TaxableBase": taxable_base,
            "CalculatedTax": abs(amount),
            "Adjustments": adjustments,
            "EntityID": self._get_entity_id(),
        }
    
    def generate_target_records(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date,
        split_count: int = 1,
        exact_match: bool = True
    ) -> List[dict]:
        """Generate Filed Tax Return records."""
        records = []
        
        if split_count == 1:
            amounts = [abs(amount)]
        else:
            amounts = self._split_amount(abs(amount), split_count)
        
        tax_type = self._get_tax_type()
        jurisdiction = self._get_jurisdiction()
        entity_id = self._get_entity_id()
        
        for i, split_amount in enumerate(amounts):
            payments = round(split_amount * random.uniform(0.8, 1.0), 2)
            refunds = round(random.uniform(0, split_amount * 0.1), 2) if random.random() < 0.15 else 0
            
            records.append({
                "TaxReturnID": f"TR{self._generate_unique_id()}",
                "TaxType": tax_type,
                "Jurisdiction": jurisdiction,
                "FilingPeriod": match_group_id,
                "ReportedTax": split_amount,
                "PaymentsMade": payments,
                "Refunds": refunds,
                "EntityID": entity_id,
            })
        
        return records
    
    def generate_unmatched_source_record(self) -> dict:
        """Generate an ERP Tax Calculation with no return match."""
        txn_date = self._generate_date()
        amount = self._generate_amount(5000, 500000)
        taxable_base = round(amount / random.uniform(0.05, 0.25), 2)
        
        return {
            "TaxType": self._get_tax_type(),
            "Jurisdiction": self._get_jurisdiction(),
            "FilingPeriod": self._get_filing_period(txn_date),
            "TransactionCount": random.randint(100, 10000),
            "TaxableBase": taxable_base,
            "CalculatedTax": amount,
            "Adjustments": round(random.uniform(-1000, 1000), 2) if random.random() < 0.2 else 0,
            "EntityID": self._get_entity_id(),
        }
    
    def generate_unmatched_target_record(self) -> dict:
        """Generate a Filed Tax Return with no ERP calculation match."""
        txn_date = self._generate_date()
        amount = self._generate_amount(5000, 500000)
        
        return {
            "TaxReturnID": f"TR{self._generate_unique_id()}",
            "TaxType": self._get_tax_type(),
            "Jurisdiction": self._get_jurisdiction(),
            "FilingPeriod": self._get_filing_period(txn_date),
            "ReportedTax": amount,
            "PaymentsMade": round(amount * random.uniform(0.8, 1.0), 2),
            "Refunds": round(random.uniform(0, amount * 0.1), 2) if random.random() < 0.15 else 0,
            "EntityID": self._get_entity_id(),
        }
