-- Dimensión de productos
CREATE TABLE IF NOT EXISTS dim_product (
    product_id SERIAL PRIMARY KEY,
    product_code VARCHAR(50) UNIQUE,
    product_name VARCHAR(255),
    category VARCHAR(100),
    active BOOLEAN DEFAULT TRUE
);

-- Clientes
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id VARCHAR(50) PRIMARY KEY,
    country VARCHAR(100)
);


-- Hechos de transacciones
CREATE TABLE IF NOT EXISTS fact_transactions (
    transaction_id SERIAL PRIMARY KEY,
    invoice VARCHAR(50),
    product_id INTEGER REFERENCES dim_product(product_id),
    customer_id VARCHAR(50)
        REFERENCES dim_customer(customer_id),
    transaction_date TIMESTAMP,
    quantity INTEGER,
    unit_price NUMERIC(12,2),
    gross_revenue NUMERIC(14,2),
    net_revenue NUMERIC(14,2),
    transaction_type VARCHAR(20),
    source VARCHAR(100)
);


-- Log de rechazos
CREATE TABLE IF NOT EXISTS quality_rejects (
    reject_id SERIAL PRIMARY KEY,
    source VARCHAR(100),
    row_data TEXT,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);