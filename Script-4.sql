-- 1. Evolución mensual de ventas netas

SELECT
    DATE_TRUNC('month', transaction_date) AS mes,
    SUM(CASE WHEN transaction_type = 'SALE'   THEN gross_revenue ELSE 0 END) AS ventas_brutas,
    SUM(CASE WHEN transaction_type = 'RETURN' THEN ABS(gross_revenue) ELSE 0 END) AS devoluciones,
    SUM(CASE WHEN transaction_type = 'SALE'   THEN gross_revenue ELSE 0 END) -
    SUM(CASE WHEN transaction_type = 'RETURN' THEN ABS(gross_revenue) ELSE 0 END) AS ventas_netas
FROM fact_transactions
GROUP BY 1
ORDER BY 1;


-- 2. Revenue bruto por categoría y proporción de devoluciones

SELECT
    p.category,
    SUM(CASE WHEN t.transaction_type = 'SALE'   THEN t.gross_revenue ELSE 0 END) AS revenue_bruto,
    SUM(CASE WHEN t.transaction_type = 'RETURN' THEN ABS(t.gross_revenue) ELSE 0 END) AS total_devoluciones,
    ROUND(
        SUM(CASE WHEN t.transaction_type = 'RETURN' THEN ABS(t.gross_revenue) ELSE 0 END) /
        NULLIF(SUM(CASE WHEN t.transaction_type = 'SALE' THEN t.gross_revenue ELSE 0 END), 0) * 100
    , 2) AS pct_devoluciones
FROM fact_transactions t
JOIN dim_product p ON t.product_id = p.product_id
GROUP BY 1
ORDER BY revenue_bruto DESC;


-- 3a. Top 10 productos por revenue neto

SELECT
    p.product_code,
    p.product_name,
    SUM(CASE WHEN t.transaction_type = 'SALE'   THEN t.gross_revenue ELSE 0 END) -
    SUM(CASE WHEN t.transaction_type = 'RETURN' THEN ABS(t.gross_revenue) ELSE 0 END) AS revenue_neto
FROM fact_transactions t
JOIN dim_product p ON t.product_id = p.product_id
GROUP BY 1, 2
ORDER BY revenue_neto DESC
LIMIT 10;



-- 3b. Top 10 productos por mayor tasa de devolución

SELECT
    p.product_code,
    p.product_name,
    COUNT(*)                                                                        AS total_transacciones,
    COUNT(CASE WHEN t.transaction_type = 'RETURN' THEN 1 END)                      AS num_devoluciones,
    ROUND(
        COUNT(CASE WHEN t.transaction_type = 'RETURN' THEN 1 END) * 100.0 /
        NULLIF(COUNT(*), 0)
    , 2)                                                                            AS tasa_devolucion_pct
FROM fact_transactions t
JOIN dim_product p ON t.product_id = p.product_id
GROUP BY 1, 2
HAVING COUNT(*) > 10
ORDER BY tasa_devolucion_pct DESC
LIMIT 10;



-- 4. Países con más transacciones y ticket promedio

SELECT
    c.country,
    COUNT(*)                                AS num_transacciones,
    ROUND(AVG(t.gross_revenue), 2)          AS ticket_promedio,
    SUM(t.gross_revenue)                    AS revenue_total
FROM fact_transactions t
JOIN dim_customer c ON t.customer_id = c.customer_id
WHERE t.transaction_type = 'SALE'
GROUP BY 1
ORDER BY num_transacciones DESC;



-- 5. Clientes identificados vs ANONYMOUS

SELECT
    CASE
        WHEN t.customer_id = 'ANONYMOUS' THEN 'Sin cliente'
        ELSE 'Identificado'
    END                                     AS tipo_cliente,
    COUNT(*)                                AS num_transacciones,
    ROUND(AVG(t.gross_revenue), 2)          AS ticket_promedio,
    SUM(t.gross_revenue)                    AS revenue_total,
    COUNT(DISTINCT t.customer_id)           AS clientes_unicos
FROM fact_transactions t
WHERE t.transaction_type = 'SALE'
GROUP BY 1;


-- 6. Productos sin descripción consistente y total códigos únicos

-- Total de códigos únicos
SELECT COUNT(DISTINCT product_code) AS total_codigos_unicos
FROM dim_product;

-- Productos con más de una variación de nombre
SELECT
    p.product_code,
    COUNT(DISTINCT p.product_name) AS variaciones_nombre,
    MIN(p.product_name)            AS ejemplo_nombre
FROM dim_product p
GROUP BY 1
HAVING COUNT(DISTINCT p.product_name) > 1
ORDER BY variaciones_nombre DESC;


-- 7. Recomendación al equipo de producto
--    Productos con alto volumen Y alta tasa de devolución

SELECT
    p.product_code,
    p.product_name,
    COUNT(*)                                                               AS total_transacciones,
    SUM(CASE WHEN t.transaction_type = 'SALE' THEN t.gross_revenue END)   AS revenue_bruto,
    COUNT(CASE WHEN t.transaction_type = 'RETURN' THEN 1 END)             AS num_devoluciones,
    ROUND(
        COUNT(CASE WHEN t.transaction_type = 'RETURN' THEN 1 END) * 100.0 /
        NULLIF(COUNT(*), 0)
    , 2)                                                                   AS tasa_devolucion_pct
FROM fact_transactions t
JOIN dim_product p ON t.product_id = p.product_id
GROUP BY 1, 2
HAVING COUNT(*) > 50
   AND COUNT(CASE WHEN t.transaction_type = 'RETURN' THEN 1 END) * 100.0 /
       NULLIF(COUNT(*), 0) > 20
ORDER BY tasa_devolucion_pct DESC
LIMIT 10;