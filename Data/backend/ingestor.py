from __future__ import annotations
import re
import pandas as pd
import numpy as np

class DataIngestor:
    """
    DataIngestor standardizes scattered and messy CSV columns into a unified financial schema.
    Inspired by soccer analytics event parsers (like SPADL).
    """

    CANONICAL_MAPPING = {
        "transaction_id": [
            "transaction_id", "txn_id", "id", "ref_no", "trx_id", 
            "reference", "tx_id", "ref", "trans_id"
        ],
        "sender_id": [
            "sender_id", "from_account", "payer_id", "originator", "sender",
            "from_ac", "sender_ac", "source_account", "source", "from", 
            "sender_acc", "from_acc"
        ],
        "receiver_id": [
            "receiver_id", "to_account", "payee_id", "beneficiary", "destination",
            "receiver", "to_ac", "receiver_ac", "dest_account", "destination_account",
            "to", "receiver_acc", "to_acc", "beneficiary_id"
        ],
        "amount": [
            "amount", "txn_amount", "transaction_amount", "amt", "value",
            "tx_amount", "sum", "val", "money", "transfer_amount"
        ],
        "timestamp": [
            "timestamp", "date", "txn_date", "created_at", "datetime",
            "time", "transaction_date", "date_time", "tx_time", "tx_date"
        ],
        "account_type": [
            "account_type", "ac_type", "type", "profile", "acc_type",
            "cust_type", "type_of_account"
        ],
        "credit_limit": [
            "credit_limit", "limit", "card_limit", "cc_limit", "max_limit"
        ]
    }

    @classmethod
    def match_column(cls, col_name: str) -> str | None:
        """Find the canonical column name for a given raw header name using synonyms and substrings."""
        normalized = str(col_name).strip().lower().replace("_", "").replace(" ", "")
        
        # 1. Exact match on normalized synonyms
        for canonical, synonyms in cls.CANONICAL_MAPPING.items():
            for syn in synonyms:
                syn_norm = syn.lower().replace("_", "").replace(" ", "")
                if normalized == syn_norm:
                    return canonical
                    
        # 2. Substring fallback match
        for canonical, synonyms in cls.CANONICAL_MAPPING.items():
            for syn in synonyms:
                syn_norm = syn.lower().replace("_", "").replace(" ", "")
                if syn_norm in normalized or normalized in syn_norm:
                    # Avoid false matching sender vs receiver if both are called 'account'
                    if canonical in ["sender_id", "receiver_id"] and len(normalized) < 5:
                        continue
                    return canonical
        return None

    @classmethod
    def clean_amount(cls, val) -> float:
        """Clean currency strings, strip symbols and commas, and cast to float."""
        if pd.isna(val) or val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        
        # String processing
        s = str(val).strip()
        # Remove currency signs and commas
        s = re.sub(r"[^\d\.\-]", "", s)
        try:
            return float(s) if s else 0.0
        except ValueError:
            return 0.0

    @classmethod
    def clean_timestamp(cls, val) -> pd.Timestamp:
        """Clean and parse varying timestamp formats, supporting epochs and custom date strings."""
        if pd.isna(val) or val is None:
            return pd.Timestamp.now()
        
        # Check if numeric (UNIX epoch)
        if isinstance(val, (int, float)) or (isinstance(val, str) and val.isdigit()):
            num = int(val)
            # Detect milliseconds vs seconds
            if num > 1e11:  # Millisecond epoch (e.g. 1716543400000)
                return pd.to_datetime(num, unit='ms', utc=True)
            else:
                return pd.to_datetime(num, unit='s', utc=True)

        try:
            # Fallback standard parsing
            return pd.to_datetime(val, errors='coerce')
        except Exception:
            return pd.Timestamp.now()

    @classmethod
    def ingest(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ingests a raw scattered dataframe and outputs a standardized canonical dataframe.
        """
        df = df.copy()
        
        # Map columns
        mapped_cols = {}
        for col in df.columns:
            canonical = cls.match_column(col)
            if canonical:
                mapped_cols[col] = canonical
                
        # Rename mapped columns
        df.rename(columns=mapped_cols, inplace=True)
        
        # Check canonical columns and inject sensible fallbacks for required columns
        # sender_id and receiver_id must exist
        if "sender_id" not in df.columns:
            # Fallback to a column that has 'from' or is first string col
            for col in df.columns:
                if col not in mapped_cols.values() and ("from" in col.lower() or "sender" in col.lower()):
                    df.rename(columns={col: "sender_id"}, inplace=True)
                    break
            else:
                # Absolute fallback: row indices
                df["sender_id"] = "SRC_IDX_" + df.index.astype(str)
                
        if "receiver_id" not in df.columns:
            for col in df.columns:
                if col not in mapped_cols.values() and ("to" in col.lower() or "receiver" in col.lower() or "beneficiary" in col.lower()):
                    df.rename(columns={col: "receiver_id"}, inplace=True)
                    break
            else:
                df["receiver_id"] = "DST_IDX_" + df.index.astype(str)

        if "amount" not in df.columns:
            # Fallback to any column with numeric elements
            for col in df.columns:
                if col not in mapped_cols.values() and any(k in col.lower() for k in ["amount", "value", "amt", "sum"]):
                    df.rename(columns={col: "amount"}, inplace=True)
                    break
            else:
                df["amount"] = 1.0  # default weight
                
        if "timestamp" not in df.columns:
            for col in df.columns:
                if col not in mapped_cols.values() and any(k in col.lower() for k in ["time", "date", "created"]):
                    df.rename(columns={col: "timestamp"}, inplace=True)
                    break
            else:
                # Create simulated dates separated by minutes
                df["timestamp"] = pd.date_range(start="2026-01-01", periods=len(df), freq="min")

        if "transaction_id" not in df.columns:
            df["transaction_id"] = "TX_" + df.index.astype(str)

        # Standardize data types
        df["transaction_id"] = df["transaction_id"].astype(str).str.strip()
        df["sender_id"] = df["sender_id"].astype(str).str.strip()
        df["receiver_id"] = df["receiver_id"].astype(str).str.strip()
        
        # Clean amount column
        df["amount"] = df["amount"].apply(cls.clean_amount)
        
        # Clean timestamp column
        df["timestamp"] = df["timestamp"].apply(cls.clean_timestamp)
        df.dropna(subset=["timestamp"], inplace=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Default optional columns if missing
        if "account_type" not in df.columns:
            df["account_type"] = "SAVINGS"  # safe default
        else:
            df["account_type"] = df["account_type"].fillna("SAVINGS").astype(str).str.upper().str.strip()

        if "credit_limit" not in df.columns:
            df["credit_limit"] = 100000.0  # default credit card limit
        else:
            df["credit_limit"] = df["credit_limit"].apply(cls.clean_amount)

        # Retain canonical columns
        cols_to_keep = ["transaction_id", "sender_id", "receiver_id", "amount", "timestamp", "account_type", "credit_limit"]
        return df[cols_to_keep]
