"""Intercompany Reconciliation scenario - Entity A vs Entity B IC Ledgers."""

from datetime import date, timedelta
from typing import List
import random

from .base import ReconciliationScenario
from ..models import ColumnDef


class IntercompanyScenario(ReconciliationScenario):
    """Intercompany reconciliation: Entity A IC Ledger vs Entity B IC Ledger.
    
    Dataset 1 (Source): Entity A Intercompany Ledger
    Dataset 2 (Target): Entity B Intercompany Ledger
    
    Common scenarios:
    - 1:1: Matching IC transactions between two entities
    - 1:N: One entity posts summary, other posts detail
    - Potential: FX differences, timing differences, document number variations
    """
    
    @property
    def name(self) -> str:
        return "intercompany"
    
    @property
    def display_name(self) -> str:
        return "Intercompany Reconciliation"
    
    @property
    def description(self) -> str:
        return "Reconcile intercompany transactions between Entity A and Entity B ledgers"
    
    @property
    def dataset1_name(self) -> str:
        return "Entity_A_IC_Ledger"
    
    @property
    def dataset2_name(self) -> str:
        return "Entity_B_IC_Ledger"
    
    @property
    def dataset1_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("ICTransactionID", "string"),  # Unique identifier
            ColumnDef("PartnerEntityCode", "string", is_key=True),  # Composite key: partner entity + document number
            ColumnDef("PostingDate", "date"),
            ColumnDef("DocumentNumber", "string", is_key=True),  # Composite key: partner entity + document number
            ColumnDef("Currency", "string"),
            ColumnDef("ICAmount", "decimal", is_monetary=True),
            ColumnDef("AccountCode", "string"),
            ColumnDef("Description", "string"),
        ]
    
    @property
    def dataset2_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("ICTransactionRef", "string"),  # Unique identifier
            ColumnDef("CounterpartyEntityCode", "string", is_key=True),  # Composite key: counterparty entity + voucher number
            ColumnDef("PostingDate", "date"),
            ColumnDef("VoucherNumber", "string", is_key=True),  # Composite key: counterparty entity + voucher number
            ColumnDef("Currency", "string"),
            ColumnDef("CorrespondingAmount", "decimal", is_monetary=True),
            ColumnDef("AccountNumber", "string"),
            ColumnDef("Memo", "string"),
        ]
    
    @property
    def primary_key_column(self) -> str:
        return "DocumentNumber"
    
    @property
    def monetary_key_column(self) -> str:
        return "ICAmount"
    
    @property
    def secondary_key_column(self) -> str:
        return "VoucherNumber"
    
    @property
    def secondary_monetary_column(self) -> str:
        return "CorrespondingAmount"
    
    def _get_entity_codes(self) -> tuple[str, str]:
        """Get a pair of entity codes for IC transaction."""
        entities = ["1000", "2000", "3000", "4000", "5000", "6000", "7000", "8000"]
        source, target = random.sample(entities, 2)
        return source, target
    
    def _get_ic_account(self) -> str:
        """Get an intercompany account code."""
        return random.choice(["211000", "211100", "211200", "131000", "131100", "131200"])
    
    def _get_ic_description(self) -> str:
        """Get an IC transaction description."""
        types = [
            "IC Management Fee", "IC Royalty", "IC Service Charge",
            "IC Cost Allocation", "IC Dividend", "IC Loan Interest",
            "IC Inventory Transfer", "IC Recharge"
        ]
        return random.choice(types)
    
    def generate_source_record(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate an Entity A IC Ledger record."""
        source_entity, partner_entity = self._get_entity_codes()
        currency = random.choice(["USD", "USD", "EUR", "GBP", "JPY"])
        description = self._get_ic_description()
        
        return {
            "ICTransactionID": f"ICA{self._generate_unique_id()}",
            "PartnerEntityCode": partner_entity,
            "PostingDate": transaction_date,
            "DocumentNumber": match_group_id,
            "Currency": currency,
            "ICAmount": abs(amount),
            "AccountCode": self._get_ic_account(),
            "Description": description,
        }
    
    def generate_target_records(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date,
        split_count: int = 1,
        exact_match: bool = True
    ) -> List[dict]:
        """Generate Entity B IC Ledger records."""
        records = []
        
        if split_count == 1:
            amounts = [abs(amount)]
        else:
            amounts = self._split_amount(abs(amount), split_count)
        
        source_entity, partner_entity = self._get_entity_codes()
        currency = random.choice(["USD", "USD", "EUR", "GBP", "JPY"])
        description = self._get_ic_description()
        
        for i, split_amount in enumerate(amounts):
            posting_date = transaction_date
            voucher = match_group_id
            
            records.append({
                "ICTransactionRef": f"ICB{self._generate_unique_id()}",
                "CounterpartyEntityCode": source_entity,
                "PostingDate": posting_date,
                "VoucherNumber": voucher,
                "Currency": currency,
                "CorrespondingAmount": split_amount,
                "AccountNumber": self._get_ic_account(),
                "Memo": description,
            })
        
        return records
    
    def generate_unmatched_source_record(self) -> dict:
        """Generate an Entity A IC record with no Entity B match."""
        txn_date = self._generate_date()
        _, partner_entity = self._get_entity_codes()
        amount = self._generate_amount(10000, 500000)
        
        return {
            "ICTransactionID": f"ICA{self._generate_unique_id()}",
            "PartnerEntityCode": partner_entity,
            "PostingDate": txn_date,
            "DocumentNumber": f"IC-{self._generate_reference_id()}",
            "Currency": random.choice(["USD", "EUR", "GBP", "JPY"]),
            "ICAmount": amount,
            "AccountCode": self._get_ic_account(),
            "Description": self._get_ic_description(),
        }
    
    def generate_unmatched_target_record(self) -> dict:
        """Generate an Entity B IC record with no Entity A match."""
        txn_date = self._generate_date()
        source_entity, _ = self._get_entity_codes()
        amount = self._generate_amount(10000, 500000)
        
        return {
            "ICTransactionRef": f"ICB{self._generate_unique_id()}",
            "CounterpartyEntityCode": source_entity,
            "PostingDate": txn_date,
            "VoucherNumber": f"IC-{self._generate_reference_id()}",
            "Currency": random.choice(["USD", "EUR", "GBP", "JPY"]),
            "CorrespondingAmount": amount,
            "AccountNumber": self._get_ic_account(),
            "Memo": self._get_ic_description(),
        }
