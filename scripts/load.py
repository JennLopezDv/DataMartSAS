import pandas as pd
import logging
from airflow.providers.postgres.hooks.postgres import PostgresHook
import io 
from io import StringIO

logger = logging.getLogger(__name__)

#Create tables if not exists.
def create_tables(**context):
    hook = PostgresHook(postgres_conn_id="postgres_dw")
    hook.run("""
        CREATE TABLE IF NOT EXISTS dim_product (
            product_id SERIAL PRIMARY KEY,
            product_code VARCHAR(50) UNIQUE,
            product_name VARCHAR(255),
            category VARCHAR(100),
            active BOOLEAN DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS dim_customer (
            customer_id VARCHAR(50) PRIMARY KEY,
            country VARCHAR(100)
        );

        CREATE TABLE IF NOT EXISTS fact_transactions (
            transaction_id SERIAL PRIMARY KEY,
            invoice VARCHAR(50),
            product_id INTEGER REFERENCES dim_product(product_id),
            customer_id VARCHAR(50) REFERENCES dim_customer(customer_id),
            transaction_date TIMESTAMP,
            quantity INTEGER,
            unit_price NUMERIC(12,2),
            gross_revenue NUMERIC(14,2),
            net_revenue NUMERIC(14,2),
            transaction_type VARCHAR(20),
            source VARCHAR(100)
        );

        CREATE TABLE IF NOT EXISTS quality_rejects (
            reject_id SERIAL PRIMARY KEY,
            source VARCHAR(100),
            row_data TEXT,
            reason VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

def load(**context):
    ti = context["ti"]
    hook = PostgresHook(postgres_conn_id="postgres_dw")
    conn = hook.get_conn()
    cursor = conn.cursor()

# Leer desde disco en lugar de XCom
    sales   = pd.read_parquet("/opt/airflow/data/sales.parquet")
    returns = pd.read_parquet("/opt/airflow/data/returns.parquet")
    rejects = pd.read_parquet("/opt/airflow/data/rejects.parquet")

    sales["invoice_date"]   = pd.to_datetime(sales["invoice_date"], utc=True).dt.tz_localize(None)
    returns["invoice_date"] = pd.to_datetime(returns["invoice_date"], utc=True).dt.tz_localize(None)

    logger.info(f"Sales: {len(sales)} | Returns: {len(returns)} | Rejects: {len(rejects)}")

    df_all = pd.concat([sales, returns], ignore_index=True)

    # --- Idempotencia ---
    execution_date = context["ds"]
    cursor.execute("DELETE FROM fact_transactions WHERE DATE(transaction_date) = %s", (execution_date,))
    logger.info(f"Registros del día {execution_date} eliminados")


#TABLES
    # --- dim_product en bloque ---

    products = df_all[["product_code", "description"]].drop_duplicates("product_code").copy()
    products.columns = ["product_code", "product_name"]
    products["category"] = "UNCLASSIFIED"
    products["active"] = True

    # Primero insertar en tabla temporal
    cursor.execute("""
        CREATE TEMP TABLE tmp_product (
            product_code VARCHAR(50),
            product_name VARCHAR(255),
            category VARCHAR(100),
            active BOOLEAN
        ) ON COMMIT DROP
    """)

    buf = StringIO()
    products.to_csv(buf, index=False, header=False)
    buf.seek(0)
    cursor.copy_expert("COPY tmp_product FROM STDIN WITH CSV", buf)

    # Luego hacer el upsert desde la temporal
    cursor.execute("""
        INSERT INTO dim_product (product_code, product_name, category, active)
        SELECT product_code, product_name, category, active FROM tmp_product
        ON CONFLICT (product_code) DO NOTHING
    """)
    logger.info(f"dim_product: {len(products)} productos procesados")

# --- dim_customer en bloque ---
    customers = df_all[["customer_id", "country"]].drop_duplicates("customer_id").copy()

    cursor.execute("""
        CREATE TEMP TABLE tmp_customer (
            customer_id VARCHAR(50),
            country VARCHAR(100)
        ) ON COMMIT DROP
    """)

    buf = StringIO()
    customers.to_csv(buf, index=False, header=False)
    buf.seek(0)
    cursor.copy_expert("COPY tmp_customer FROM STDIN WITH CSV", buf)

    cursor.execute("""
        INSERT INTO dim_customer (customer_id, country)
        SELECT customer_id, country FROM tmp_customer
        ON CONFLICT (customer_id) DO NOTHING
    """)
    logger.info(f"dim_customer: {len(customers)} clientes procesados")

    # --- fact_transactions en bloque ---
    # Traer product_id desde la BD
    cursor.execute("SELECT product_code, product_id FROM dim_product")
    product_map = {row[0]: row[1] for row in cursor.fetchall()}

    df_all["product_id"] = df_all["product_code"].map(product_map)
    df_all = df_all.dropna(subset=["product_id"])
    df_all["product_id"] = df_all["product_id"].astype(int)

    facts = df_all[[
        "invoice", "product_id", "customer_id",
        "invoice_date", "quantity", "unit_price",
        "gross_revenue", "gross_revenue",
        "transaction_type", "source"
    ]].copy()
    facts.columns = [
        "invoice", "product_id", "customer_id",
        "transaction_date", "quantity", "unit_price",
        "gross_revenue", "net_revenue",
        "transaction_type", "source"
    ]

    buf = StringIO()
    facts.to_csv(buf, index=False, header=False)
    buf.seek(0)
    cursor.copy_expert("""
        COPY fact_transactions (
            invoice, product_id, customer_id,
            transaction_date, quantity, unit_price,
            gross_revenue, net_revenue,
            transaction_type, source
        ) FROM STDIN WITH CSV
    """, buf)
    logger.info(f"fact_transactions: {len(facts)} filas insertadas")

    # --- quality_rejects en bloque ---
    if not rejects.empty:
        rej = rejects[["source", "reject_reason"]].copy()
        rej["row_data"] = rejects.drop(columns=["source", "reject_reason"], errors="ignore").astype(str).apply(lambda r: r.to_json(), axis=1)
        rej = rej[["source", "row_data", "reject_reason"]]

        buf = StringIO()
        rej.to_csv(buf, index=False, header=False, quoting=1)
        buf.seek(0)
        cursor.copy_expert("""
            COPY quality_rejects (source, row_data, reason)
            FROM STDIN WITH CSV QUOTE '"'
        """, buf)
        logger.info(f"quality_rejects: {len(rej)} rechazos insertados")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Carga completa")