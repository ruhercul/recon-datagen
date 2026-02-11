"""Bank Reconciliation scenario - Cash Ledger vs Bank Statement."""

from datetime import date, timedelta
from typing import List
import random

from .base import ReconciliationScenario
from ..models import ColumnDef


class BankReconciliationScenario(ReconciliationScenario):
    """Bank reconciliation: Cash Ledger vs Bank Statement.
    
    Dataset 1 (Source): Cash Ledger
    Dataset 2 (Target): Bank Statement
    
    Common scenarios:
    - 1:1: Single ledger entry matches single bank transaction
    - 1:N: Multiple ledger entries match one bank deposit
    - Potential: Timing differences, amount discrepancies
    """
    
    @property
    def name(self) -> str:
        return "bank-recon"
    
    @property
    def display_name(self) -> str:
        return "Bank Reconciliation"
    
    @property
    def description(self) -> str:
        return "Reconcile Cash Ledger entries against Bank Statement transactions"
    
    @property
    def dataset1_name(self) -> str:
        return "Cash_Ledger"
    
    @property
    def dataset2_name(self) -> str:
        return "Bank_Statement"
    
    @property
    def dataset1_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("TransactionID", "string", is_key=True),
            ColumnDef("PostingDate", "date"),
            ColumnDef("DocumentNumber", "string", is_key=True),
            ColumnDef("PayeeName", "string"),
            ColumnDef("Description", "string"),
            ColumnDef("Currency", "string"),
            ColumnDef("Amount", "decimal", is_monetary=True),
            ColumnDef("DebitCredit", "string"),
        ]
    
    @property
    def dataset2_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("BankTransactionID", "string", is_key=True),
            ColumnDef("TransactionDate", "date"),
            ColumnDef("ClearingDate", "date"),
            ColumnDef("BankReference", "string", is_key=True),
            ColumnDef("Counterparty", "string"),
            ColumnDef("Narrative", "string"),
            ColumnDef("Currency", "string"),
            ColumnDef("BankAmount", "decimal", is_monetary=True),
        ]
    
    @property
    def primary_key_column(self) -> str:
        return "DocumentNumber"
    
    @property
    def secondary_key_column(self) -> str:
        return "BankReference"
    
    @property
    def monetary_key_column(self) -> str:
        return "Amount"
    
    @property
    def secondary_monetary_column(self) -> str:
        return "BankAmount"
    
    def _generate_payee(self) -> str:
        """Generate a realistic payee name."""
        return self.faker.company()
    
    def _generate_description(self, payee: str, dc: str) -> str:
        """Generate transaction description."""
        if dc == "D":
            prefixes = ["Payment to", "Wire to", "ACH to", "Check to"]
        else:
            prefixes = ["Receipt from", "Wire from", "ACH from", "Deposit from"]
        return f"{random.choice(prefixes)} {payee}"
    
    def _generate_narrative(self, payee: str, ref: str) -> str:
        """Generate bank narrative."""
        types = ["WIRE", "ACH", "CHK", "DEP", "TRF"]
        return f"{random.choice(types)} {ref} {payee[:20]}"
    
    def generate_source_record(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate a Cash Ledger record."""
        dc = "D" if random.random() < 0.6 else "C"
        payee = self._generate_payee()
        currency = random.choice(["USD", "USD", "USD", "EUR", "GBP"])
        
        return {
            "TransactionID": f"TXN{self._generate_unique_id()}",
            "PostingDate": transaction_date,
            "DocumentNumber": match_group_id,
            "PayeeName": payee,
            "Description": self._generate_description(payee, dc),
            "Currency": currency,
            "Amount": abs(amount),
            "DebitCredit": dc,
        }
    
    def generate_target_records(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date,
        split_count: int = 1,
        exact_match: bool = True
    ) -> List[dict]:
        """Generate Bank Statement records."""
        records = []
        
        if split_count == 1:
            amounts = [abs(amount)]
        else:
            amounts = self._split_amount(abs(amount), split_count)
        
        payee = self._generate_payee()
        currency = random.choice(["USD", "USD", "USD", "EUR", "GBP"])
        
        for i, split_amount in enumerate(amounts):
            # Always produce an exact match here; the generator's
            # apply_variance step handles potential-match mutations.
            clearing_date = transaction_date
            ref = match_group_id if split_count == 1 else f"{match_group_id}-{i+1:02d}"
            
            records.append({
                "BankTransactionID": f"BNK{self._generate_unique_id()}",
                "TransactionDate": transaction_date,
                "ClearingDate": clearing_date,
                "BankReference": ref,
                "Counterparty": payee,
                "Narrative": self._generate_narrative(payee, ref),
                "Currency": currency,
                "BankAmount": split_amount,
            })
        
        return records
    
    def generate_unmatched_source_record(self) -> dict:
        """Generate a Cash Ledger record with no bank match."""
        txn_date = self._generate_date()
        payee = self._generate_payee()
        dc = random.choice(["D", "C"])
        amount = self._generate_amount(100, 25000)
        
        return {
            "TransactionID": f"TXN{self._generate_unique_id()}",
            "PostingDate": txn_date,
            "DocumentNumber": f"DOC-{self._generate_reference_id()}",
            "PayeeName": payee,
            "Description": self._generate_description(payee, dc),
            "Currency": random.choice(["USD", "EUR", "GBP"]),
            "Amount": amount,
            "DebitCredit": dc,
        }
    
    def generate_unmatched_target_record(self) -> dict:
        """Generate a Bank Statement record with no ledger match."""
        txn_date = self._generate_date()
        payee = self._generate_payee()
        ref = f"BNK-{self._generate_reference_id()}"
        amount = self._generate_amount(50, 15000)
        
        return {
            "BankTransactionID": f"BNK{self._generate_unique_id()}",
            "TransactionDate": txn_date,
            "ClearingDate": txn_date + timedelta(days=random.randint(1, 3)),
            "BankReference": ref,
            "Counterparty": payee,
            "Narrative": self._generate_narrative(payee, ref),
            "Currency": random.choice(["USD", "EUR", "GBP"]),
            "BankAmount": amount,
        }
