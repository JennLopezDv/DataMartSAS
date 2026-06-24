import pandas as pd
import json
import logging
from airflow.models import Variable

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    # source_1 
    "InvoiceNo":   "invoice",
    "StockCode":   "product_code",
    "Description": "description",
    "Quantity":    "quantity",
    "InvoiceDate": "invoice_date",
    "UnitPrice":   "unit_price",
    "CustomerID":  "customer_id",
    "Country":     "country",
    # source_2 
    "Invoice":     "invoice",
    "StockCode":   "product_code",
    "Description": "description",
    "Quantity":    "quantity",
    "InvoiceDate": "invoice_date",
    "Price":       "unit_price",
    "Customer ID": "customer_id",
    "Country":     "country",
}

def transform(**context):
    ti = context["ti"]
    
    # Leer desde disco
    df1 = pd.read_parquet("/opt/airflow/data/raw_source_1.parquet")
    df2 = pd.read_parquet("/opt/airflow/data/raw_source_2.parquet")
    
    # Renombrar columnas al esquema canónico
    df1 = df1.rename(columns=COLUMN_MAP)
    df2 = df2.rename(columns=COLUMN_MAP)
    df1["source"] = "source_1"
    df2["source"] = "source_2"
    
    # Unir ambas fuentes
    df = pd.concat([df1, df2], ignore_index=True)
    
    # --- Normalización ---
    df["product_code"] = df["product_code"].str.upper().str.strip()
    df["quantity"]     = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"]   = pd.to_numeric(df["unit_price"], errors="coerce")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce", utc=True)
    df["customer_id"]  = df["customer_id"].fillna("ANONYMOUS")
    df["description"]  = df["description"].str.upper().str.strip()
    
    # --- Separar rechazos ---

    rejects_list = []

    mask_price = df["unit_price"] <= 0
    rejects_list.append(df[mask_price].assign(reject_reason="unit_price <= 0"))
    df = df[~mask_price]

    mask_date = df["invoice_date"].isna()
    rejects_list.append(df[mask_date].assign(reject_reason="fecha invalida"))
    df = df[~mask_date]

    # Convertir lista a DataFrame antes de guardar
    rejects = pd.concat(rejects_list, ignore_index=True) if rejects_list else pd.DataFrame()

    # --- Deduplicación entre fuentes ---
    df = df.drop_duplicates(subset=["invoice", "product_code", "quantity", "invoice_date"])

    # --- Separar ventas y devoluciones ---
    sales   = df[df["quantity"] > 0].copy()
    returns = df[df["quantity"] <= 0].copy()

    # --- Calcular revenue ---
    sales["gross_revenue"] = sales["quantity"] * sales["unit_price"]
    sales["transaction_type"] = "SALE"
    returns["gross_revenue"] = returns["quantity"] * returns["unit_price"]
    returns["transaction_type"] = "RETURN"

    # --- Guardar en disco ---
    sales.to_parquet("/opt/airflow/data/sales.parquet", index=False)
    returns.to_parquet("/opt/airflow/data/returns.parquet", index=False)
    rejects.to_parquet("/opt/airflow/data/rejects.parquet", index=False)

    logger.info(f"Ventas: {len(sales)} | Devoluciones: {len(returns)} | Rechazos: {len(rejects)}")
    return f"ventas={len(sales)}, devoluciones={len(returns)}, rechazos={len(rejects)}"