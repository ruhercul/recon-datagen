"""Fixed Asset Reconciliation scenario - FA Register vs GL FA Accounts."""

from datetime import date, timedelta
from typing import List
import random

from .base import ReconciliationScenario
from ..models import ColumnDef


class FixedAssetReconciliationScenario(ReconciliationScenario):
    """Fixed Asset reconciliation: Fixed Asset Register vs GL Fixed Asset Accounts.
    
    Dataset 1 (Source): Fixed Asset Register
    Dataset 2 (Target): GL Fixed Asset Accounts
    
    Common scenarios:
    - 1:1: Single asset matches single GL entry
    - 1:N: Single asset with multiple GL entries (additions, disposals)
    - Potential: Depreciation calculation differences, timing variances
    """
    
    @property
    def name(self) -> str:
        return "fixed-asset-recon"
    
    @property
    def display_name(self) -> str:
        return "Fixed Asset Reconciliation"
    
    @property
    def description(self) -> str:
        return "Reconcile Fixed Asset Register against GL Fixed Asset Accounts"
    
    @property
    def dataset1_name(self) -> str:
        return "FA_Register"
    
    @property
    def dataset2_name(self) -> str:
        return "GL_FA_Accounts"
    
    @property
    def dataset1_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("AssetID", "string", is_key=True),
            ColumnDef("AssetTag", "string"),
            ColumnDef("AssetName", "string"),
            ColumnDef("DepreciationPeriod", "string", is_key=True),
            ColumnDef("AcquisitionDate", "date"),
            ColumnDef("Cost", "decimal"),
            ColumnDef("AccumulatedDepreciation", "decimal"),
            ColumnDef("NetBookValue", "decimal", is_monetary=True),
        ]
    
    @property
    def dataset2_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("Period", "string", is_key=True),
            ColumnDef("GLAccount", "string"),
            ColumnDef("FAAssetID", "string", is_key=True),
            ColumnDef("OpeningCost", "decimal"),
            ColumnDef("Additions", "decimal"),
            ColumnDef("Disposals", "decimal"),
            ColumnDef("DepreciationExpense", "decimal"),
            ColumnDef("EndingNBV", "decimal", is_monetary=True),
        ]
    
    @property
    def primary_key_column(self) -> str:
        return "AssetID"
    
    @property
    def monetary_key_column(self) -> str:
        return "NetBookValue"
    
    @property
    def secondary_key_column(self) -> str:
        return "FAAssetID"
    
    @property
    def secondary_monetary_column(self) -> str:
        return "EndingNBV"
    
    def _generate_asset_name(self) -> str:
        """Generate a realistic asset name."""
        categories = [
            ("Computer Equipment", ["Laptop", "Desktop", "Server", "Monitor", "Printer"]),
            ("Furniture", ["Desk", "Chair", "Cabinet", "Table", "Shelving"]),
            ("Vehicle", ["Truck", "Van", "Forklift", "Car", "Trailer"]),
            ("Machinery", ["CNC Machine", "Press", "Conveyor", "Pump", "Generator"]),
            ("Building", ["Office Building", "Warehouse", "Factory", "Storage Unit"]),
        ]
        category, items = random.choice(categories)
        item = random.choice(items)
        return f"{item} - {self.faker.city()}"
    
    def _get_gl_account(self) -> str:
        """Get a FA GL account."""
        return random.choice(["150000", "151000", "152000", "153000", "154000", "155000"])
    
    def _get_period(self, txn_date: date) -> str:
        """Get fiscal period from date."""
        return f"{txn_date.year}-{txn_date.month:02d}"
    
    def generate_source_record(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate a Fixed Asset Register record."""
        cost = round(random.uniform(5000, 500000), 2)
        accum_depr = round(cost * random.uniform(0.1, 0.8), 2)
        nbv = round(cost - accum_depr, 2)
        
        # Override NBV with the amount parameter for matching
        nbv = abs(amount)
        
        return {
            "AssetID": match_group_id,
            "AssetTag": f"TAG-{random.randint(10000, 99999)}",
            "AssetName": self._generate_asset_name(),
            "DepreciationPeriod": self._get_period(transaction_date),
            "AcquisitionDate": transaction_date - timedelta(days=random.randint(365, 1825)),
            "Cost": cost,
            "AccumulatedDepreciation": accum_depr,
            "NetBookValue": nbv,
        }
    
    def generate_target_records(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date,
        split_count: int = 1,
        exact_match: bool = True
    ) -> List[dict]:
        """Generate GL Fixed Asset Account records."""
        records = []
        
        if split_count == 1:
            amounts = [abs(amount)]
        else:
            amounts = self._split_amount(abs(amount), split_count)
        
        period = self._get_period(transaction_date)
        gl_account = self._get_gl_account()
        
        for i, split_amount in enumerate(amounts):
            opening_cost = round(random.uniform(5000, 500000), 2)
            additions = round(random.uniform(0, opening_cost * 0.1), 2) if random.random() < 0.2 else 0
            disposals = round(random.uniform(0, opening_cost * 0.05), 2) if random.random() < 0.1 else 0
            depr_expense = round(random.uniform(100, 5000), 2)
            
            records.append({
                "Period": period,
                "GLAccount": gl_account,
                "FAAssetID": match_group_id,
                "OpeningCost": opening_cost,
                "Additions": additions,
                "Disposals": disposals,
                "DepreciationExpense": depr_expense,
                "EndingNBV": split_amount,
            })
        
        return records
    
    def generate_unmatched_source_record(self) -> dict:
        """Generate a FA Register record with no GL match."""
        txn_date = self._generate_date()
        cost = round(random.uniform(5000, 500000), 2)
        accum_depr = round(cost * random.uniform(0.1, 0.8), 2)
        
        return {
            "AssetID": f"FA-{self._generate_reference_id()}",
            "AssetTag": f"TAG-{random.randint(10000, 99999)}",
            "AssetName": self._generate_asset_name(),
            "DepreciationPeriod": self._get_period(txn_date),
            "AcquisitionDate": txn_date - timedelta(days=random.randint(365, 1825)),
            "Cost": cost,
            "AccumulatedDepreciation": accum_depr,
            "NetBookValue": round(cost - accum_depr, 2),
        }
    
    def generate_unmatched_target_record(self) -> dict:
        """Generate a GL FA Account record with no register match."""
        txn_date = self._generate_date()
        opening_cost = round(random.uniform(5000, 500000), 2)
        
        return {
            "Period": self._get_period(txn_date),
            "GLAccount": self._get_gl_account(),
            "FAAssetID": f"FA-{self._generate_reference_id()}",
            "OpeningCost": opening_cost,
            "Additions": 0,
            "Disposals": 0,
            "DepreciationExpense": round(random.uniform(100, 5000), 2),
            "EndingNBV": round(opening_cost * random.uniform(0.2, 0.9), 2),
        }
