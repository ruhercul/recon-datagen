"""Expense Reconciliation scenario - T&E Reports vs Corporate Card Statement."""

from datetime import date, timedelta
from typing import List
import random

from .base import ReconciliationScenario
from ..models import ColumnDef


class ExpenseReconciliationScenario(ReconciliationScenario):
    """Expense reconciliation: T&E Expense Reports vs Corporate Card Statement.
    
    Dataset 1 (Source): T&E Expense Reports
    Dataset 2 (Target): Corporate Card Statement
    
    Common scenarios:
    - 1:1: Single expense claim matches single card transaction
    - 1:N: Single expense report with multiple card charges
    - Potential: Amount differences (tips, FX), merchant name variations
    """
    
    @property
    def name(self) -> str:
        return "expense-recon"
    
    @property
    def display_name(self) -> str:
        return "Expense Reconciliation"
    
    @property
    def description(self) -> str:
        return "Reconcile T&E Expense Reports against Corporate Card Statements"
    
    @property
    def dataset1_name(self) -> str:
        return "Expense_Reports"
    
    @property
    def dataset2_name(self) -> str:
        return "Card_Statement"
    
    @property
    def dataset1_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("ReportID", "string", is_key=True),
            ColumnDef("EmployeeID", "string", is_key=True),
            ColumnDef("EmployeeName", "string"),
            ColumnDef("ReportDate", "date"),
            ColumnDef("MerchantName", "string"),
            ColumnDef("ExpenseCategory", "string"),
            ColumnDef("Currency", "string"),
            ColumnDef("AmountClaimed", "decimal", is_monetary=True),
        ]
    
    @property
    def dataset2_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("CardTransactionID", "string", is_key=True),
            ColumnDef("CardholderEmployeeID", "string", is_key=True),
            ColumnDef("PostingDate", "date"),
            ColumnDef("Merchant", "string"),
            ColumnDef("MCC", "string"),
            ColumnDef("Currency", "string"),
            ColumnDef("BilledAmount", "decimal", is_monetary=True),
            ColumnDef("AuthorizationCode", "string"),
        ]
    
    @property
    def primary_key_column(self) -> str:
        return "ReportID"
    
    @property
    def monetary_key_column(self) -> str:
        return "AmountClaimed"
    
    @property
    def secondary_key_column(self) -> str:
        return "AuthorizationCode"
    
    @property
    def secondary_monetary_column(self) -> str:
        return "BilledAmount"
    
    def _get_merchant_and_category(self) -> tuple[str, str, str]:
        """Get merchant name, category, and MCC code."""
        merchants = [
            ("United Airlines", "TRAVEL", "4511"),
            ("Delta Air Lines", "TRAVEL", "4511"),
            ("American Airlines", "TRAVEL", "4511"),
            ("Marriott Hotels", "LODGING", "7011"),
            ("Hilton Hotels", "LODGING", "7011"),
            ("Hyatt Hotels", "LODGING", "7011"),
            ("Hertz Car Rental", "CAR_RENTAL", "7512"),
            ("Enterprise Rent-A-Car", "CAR_RENTAL", "7512"),
            ("Uber", "GROUND_TRANSPORT", "4121"),
            ("Lyft", "GROUND_TRANSPORT", "4121"),
            ("The Capital Grille", "MEALS", "5812"),
            ("Ruth's Chris Steak House", "MEALS", "5812"),
            ("Starbucks", "MEALS", "5814"),
            ("Office Depot", "SUPPLIES", "5943"),
            ("Staples", "SUPPLIES", "5943"),
            ("Amazon Business", "SUPPLIES", "5999"),
            ("FedEx", "SHIPPING", "4215"),
            ("UPS", "SHIPPING", "4215"),
        ]
        merchant, category, mcc = random.choice(merchants)
        return merchant, category, mcc
    
    def _get_cost_center(self) -> str:
        """Get a cost center code."""
        return f"CC{random.randint(100, 999)}"
    
    def generate_source_record(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate a T&E Expense Report record."""
        merchant, category, _ = self._get_merchant_and_category()
        self._last_employee_id = f"EMP{random.randint(10000, 99999)}"
        currency = random.choice(["USD", "USD", "USD", "EUR", "GBP"])
        self._last_currency = currency
        
        return {
            "ReportID": match_group_id,
            "EmployeeID": self._last_employee_id,
            "EmployeeName": self.faker.name(),
            "ReportDate": transaction_date,
            "MerchantName": merchant,
            "ExpenseCategory": category,
            "Currency": currency,
            "AmountClaimed": abs(amount),
        }
    
    def generate_target_records(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date,
        split_count: int = 1,
        exact_match: bool = True
    ) -> List[dict]:
        """Generate Corporate Card Statement records."""
        records = []
        
        if split_count == 1:
            amounts = [abs(amount)]
        else:
            amounts = self._split_amount(abs(amount), split_count)
        
        # Reuse the employee ID from the source so the records can match
        employee_id = getattr(self, '_last_employee_id', f"EMP{random.randint(10000, 99999)}")
        currency = getattr(self, '_last_currency', random.choice(["USD", "EUR", "GBP"]))
        
        for i, split_amount in enumerate(amounts):
            merchant, _, mcc = self._get_merchant_and_category()
            ref = match_group_id if split_count == 1 else f"{match_group_id}-{i+1:02d}"
            
            records.append({
                "CardTransactionID": f"CTX{self._generate_unique_id()}",
                "CardholderEmployeeID": employee_id,
                "PostingDate": transaction_date,
                "Merchant": merchant,
                "MCC": mcc,
                "Currency": currency,
                "BilledAmount": split_amount,
                "AuthorizationCode": ref,
            })
        
        return records
    
    def generate_unmatched_source_record(self) -> dict:
        """Generate an Expense Report with no card match."""
        txn_date = self._generate_date()
        merchant, category, _ = self._get_merchant_and_category()
        amount = self._generate_amount(25, 2500)
        
        return {
            "ReportID": f"EXP-{self._generate_reference_id()}",
            "EmployeeID": f"EMP{random.randint(10000, 99999)}",
            "EmployeeName": self.faker.name(),
            "ReportDate": txn_date,
            "MerchantName": merchant,
            "ExpenseCategory": category,
            "Currency": random.choice(["USD", "EUR", "GBP"]),
            "AmountClaimed": amount,
        }
    
    def generate_unmatched_target_record(self) -> dict:
        """Generate a Card Statement record with no expense report match."""
        txn_date = self._generate_date()
        merchant, _, mcc = self._get_merchant_and_category()
        amount = self._generate_amount(25, 2500)
        
        return {
            "CardTransactionID": f"CTX{self._generate_unique_id()}",
            "CardholderEmployeeID": f"EMP{random.randint(10000, 99999)}",
            "PostingDate": txn_date,
            "Merchant": merchant,
            "MCC": mcc,
            "Currency": random.choice(["USD", "EUR", "GBP"]),
            "BilledAmount": amount,
            "AuthorizationCode": f"{random.randint(100000, 999999)}",
        }
