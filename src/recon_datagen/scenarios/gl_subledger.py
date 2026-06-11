"""GL vs Subledger Reconciliation scenario."""

from datetime import date, timedelta
from typing import List
import random

from .base import ReconciliationScenario
from ..models import ColumnDef


class GLSubledgerScenario(ReconciliationScenario):
    """GL vs Subledger reconciliation: General Ledger Summary vs Subledger Detail.
    
    Dataset 1 (Source): General Ledger Summary
    Dataset 2 (Target): Subledger Detail (AP/AR)
    
    Common scenarios:
    - 1:1: Single GL summary matches aggregated subledger
    - 1:N: GL summary matches multiple subledger transactions
    - Potential: Rounding differences, period timing issues
    """
    
    @property
    def name(self) -> str:
        return "gl-subledger"
    
    @property
    def display_name(self) -> str:
        return "GL vs Subledger Reconciliation"
    
    @property
    def description(self) -> str:
        return "Reconcile General Ledger Summary against Subledger Detail transactions"
    
    @property
    def dataset1_name(self) -> str:
        return "GL_Summary"
    
    @property
    def dataset2_name(self) -> str:
        return "Subledger_Detail"
    
    @property
    def dataset1_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("AccountCode", "string", is_key=True),  # Composite key: account code + period
            ColumnDef("Period", "string", is_key=True),  # Composite key: account code + period
            ColumnDef("BeginningBalance", "decimal"),
            ColumnDef("Debits", "decimal", is_monetary=True),
            ColumnDef("Credits", "decimal"),
            ColumnDef("EndingBalance", "decimal"),
            ColumnDef("Currency", "string"),
            ColumnDef("CostCenter", "string"),
        ]
    
    @property
    def dataset2_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("SubledgerTransactionID", "string"),  # Unique identifier
            ColumnDef("MappedAccountCode", "string", is_key=True),  # Composite key: mapped account + period
            ColumnDef("Period", "string", is_key=True),  # Composite key: mapped account + period
            ColumnDef("TransactionDate", "date"),
            ColumnDef("DocumentNumber", "string"),
            ColumnDef("Currency", "string"),
            ColumnDef("DetailAmount", "decimal", is_monetary=True),
            ColumnDef("CostCenter", "string"),
        ]
    
    @property
    def primary_key_column(self) -> str:
        return "AccountCode"
    
    @property
    def monetary_key_column(self) -> str:
        return "Debits"
    
    @property
    def secondary_key_column(self) -> str:
        return "MappedAccountCode"
    
    @property
    def secondary_monetary_column(self) -> str:
        return "DetailAmount"
    
    def _get_gl_account(self) -> tuple[str, str]:
        """Get GL account code and type."""
        accounts = [
            ("120000", "AR"), ("121000", "AR"), ("122000", "AR"),
            ("200000", "AP"), ("201000", "AP"), ("202000", "AP"),
            ("130000", "INV"), ("131000", "INV"),
            ("150000", "FA"), ("151000", "FA"),
        ]
        return random.choice(accounts)
    
    def _get_period(self, txn_date: date) -> str:
        """Get fiscal period from date."""
        return f"{txn_date.year}-{txn_date.month:02d}"
    
    def _get_cost_center(self) -> str:
        """Get a cost center code."""
        return f"CC{random.randint(100, 999)}"
    
    def generate_source_record(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate a GL Summary record."""
        account_code, _ = self._get_gl_account()
        period = self._get_period(transaction_date)
        currency = random.choice(["USD", "USD", "USD", "EUR"])
        cost_center = self._get_cost_center()
        
        beginning = round(random.uniform(10000, 500000), 2)
        debits = abs(amount)
        credits = round(debits * random.uniform(0.3, 0.7), 2)
        ending = round(beginning + debits - credits, 2)
        
        return {
            "AccountCode": match_group_id,
            "Period": period,
            "BeginningBalance": beginning,
            "Debits": debits,
            "Credits": credits,
            "EndingBalance": ending,
            "Currency": currency,
            "CostCenter": cost_center,
        }
    
    def generate_target_records(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date,
        split_count: int = 1,
        exact_match: bool = True
    ) -> List[dict]:
        """Generate Subledger Detail records."""
        records = []
        
        if split_count == 1:
            amounts = [abs(amount)]
        else:
            amounts = self._split_amount(abs(amount), split_count)
        
        account_code, _ = self._get_gl_account()
        period = self._get_period(transaction_date)
        currency = random.choice(["USD", "USD", "USD", "EUR"])
        cost_center = self._get_cost_center()
        
        for i, split_amount in enumerate(amounts):
            records.append({
                "SubledgerTransactionID": f"SL{self._generate_unique_id()}",
                "MappedAccountCode": match_group_id,
                "Period": period,
                "TransactionDate": transaction_date,
                "DocumentNumber": f"DOC-{random.randint(100000, 999999)}",
                "Currency": currency,
                "DetailAmount": split_amount,
                "CostCenter": cost_center,
            })
        
        return records
    
    def generate_unmatched_source_record(self) -> dict:
        """Generate a GL Summary record with no subledger match."""
        txn_date = self._generate_date()
        account_code, _ = self._get_gl_account()
        amount = self._generate_amount(5000, 250000)
        
        beginning = round(random.uniform(10000, 500000), 2)
        credits = round(amount * random.uniform(0.3, 0.7), 2)
        
        return {
            "AccountCode": account_code,
            "Period": self._get_period(txn_date),
            "BeginningBalance": beginning,
            "Debits": amount,
            "Credits": credits,
            "EndingBalance": round(beginning + amount - credits, 2),
            "Currency": random.choice(["USD", "EUR"]),
            "CostCenter": self._get_cost_center(),
        }
    
    def generate_unmatched_target_record(self) -> dict:
        """Generate a Subledger Detail record with no GL match."""
        txn_date = self._generate_date()
        account_code, _ = self._get_gl_account()
        amount = self._generate_amount(100, 50000)
        
        return {
            "SubledgerTransactionID": f"SL{self._generate_unique_id()}",
            "MappedAccountCode": account_code,
            "Period": self._get_period(txn_date),
            "TransactionDate": txn_date,
            "DocumentNumber": f"DOC-{random.randint(100000, 999999)}",
            "Currency": random.choice(["USD", "EUR"]),
            "DetailAmount": amount,
            "CostCenter": self._get_cost_center(),
        }
