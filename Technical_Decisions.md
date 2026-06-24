# Technical Decisions Document
## ETL Pipeline — DataMart S.A.S.

---

## 1. Design of the Analytical Repository Model

The analytical repository was designed with a simple star schema consisting of four tables:

- **`dim_product`** — product dimension with standardized code, canonical name, category, and active status.
- **`dim_customer`** — customer dimension with identifier and country.
- **`fact_transactions`** — a fact table that centralizes both sales and returns, differentiated by the `transaction_type` column (`SALE` or `RETURN`). It stores gross revenue per transaction line.
- **`quality_rejects`** — log table for records rejected during transformation, including the reason for rejection and the source.

This design allows all business questions to be answered using simple joins between the fact table and the dimensions, and enables the calculation of net sales by filtering or grouping by `transaction_type`.

---
## 2. Resolving Ambiguous Cases

### 2.1 Transactions Without a `customer_id`

**Decision:** These were included in the analysis by assigning them the value `ANONYMOUS` as the customer identifier.

**Justification:** Excluding them would have removed a significant volume of actual transactions with associated revenue, which would distort the sales totals and the analysis by country. By keeping them under a special identifier, it is possible to segment them and compare their behavior against identified customers, which also directly answers business question number 5 in the statement.

**Documented Impact:** `ANONYMOUS` customers account for a significant proportion of transactions. Their average ticket and total revenue metrics are visible in the SQL query for Question 5.

---

### 2.2 Canonical Product Names

**Decision:** Each product description was normalized to uppercase with no leading or trailing spaces (`str.upper().str.strip()`). In cases where multiple variations existed for the same product code, the first description found after normalization was selected.

**Justification:** Normalizing to uppercase eliminates capitalization variations (`Candle Holder White`, `candle holder white`, `CANDLE HOLDER WHITE`) without requiring additional voting or frequency logic. It is a simple rule that can be consistently applied to all records and is reproducible in any pipeline run.

---
### 2.3 Duplicates Between the Two Data Sources

**Decision:** Duplicates were detected and removed using a composite key consisting of four fields:

```
invoice + product_code + quantity + invoice_date
```

Neither source takes precedence over the other. When two records from different sources match in all fields of the key, the first one to appear after concatenating `source_1` (data.csv) followed by `source_2` (online_retail_II.xlsx) is retained.

**Rationale:** A composite key is more reliable than blindly prioritizing one source, since overlapping dates between datasets do not necessarily mean that all records for that period are duplicates. A record is discarded only when all four fields match exactly, which strongly indicates that it is the same transaction reported in both sources.

---
### 2.4 Records with a unit price less than or equal to zero

**Decision:** Records with `unit_price <= 0` were rejected and logged in the `quality_rejects` table with the reason `“unit_price <= 0”`. They were not included as either sales or returns.

**Justification:** The statement explicitly states that the unit price cannot be zero or negative in a valid sale. Since there is no business rule explaining what a negative price represents (it could be an adjustment, a system error, or an incorrectly recorded discount), the safest decision is to reject them and leave a trace in the log so that the business team can review them manually.

---

### 2.5 Transactions with a quantity less than or equal to zero

**Decision:** These were classified as returns (`transaction_type = ‘RETURN’`) and stored in the same `fact_transactions` table alongside normal sales.

**Rationale:** Keeping them in the same table makes it easier to calculate net revenue with a single aggregation query filtered by `transaction_type`, without the need for joins between separate tables. The sign of the amount and the revenue unequivocally identifies them as returns.

---

## 3. DAG Idempotency Guarantee

The DAG is idempotent by design: running it twice on the same day with the same data produces exactly the same result in the analytics repository.

This is achieved through a `DELETE` operation at the beginning of the `load` task, which deletes all records from `fact_transactions` whose `transaction_date` matches the DAG’s execution date (`context[“ds”]`) before inserting the new ones:

```sql
DELETE FROM fact_transactions
WHERE DATE(transaction_date) = '{{ ds }}'
```

The `dim_product` and `dim_customer` dimensions use `ON CONFLICT DO NOTHING`, which ensures that a second run does not duplicate existing products or customers.

---
## 4. Decision on Data Transfer Between Tasks

**Decision:** Intermediate DataFrames (sales, returns, rejections) are saved to Parquet files in `/opt/airflow/data/` instead of using Airflow's XCom.

**Rationale:** The combined dataset exceeds 500,000 records. Serializing that volume into JSON for XCom consumed more than 500 MB of memory per task and caused the process to receive a SIGTERM due to insufficient resources. Parquet files resolve this issue because they are a compressed, columnar format, and the `/opt/airflow/data/` directory is mounted as a shared volume between the scheduler and the workers, ensuring that all tasks access the same files.

---
## 5. Product Categorization Strategy

Since the optional product API was not implemented, all products were classified under the `UNCLASSIFIED` category by default, controlled by the Airflow variable `DEFAULT_CATEGORY`. This decision is documented and can be overridden in a future iteration by connecting the API or loading a static mapping file from codes to categories.

---

## 6. Schema Unification Between Sources

The two sources have different column names for the same fields. An explicit renaming map was applied in `transform.py`:

| Source 1 | Source 2 | Canonical Name |
|---|---|---|
| InvoiceNo | Invoice | invoice |
| StockCode | StockCode | product_code |
| UnitPrice | Price | unit_price |
| CustomerID | Customer ID | customer_id |
| InvoiceDate | InvoiceDate | invoice_date |

All date fields were standardized to UTC and then converted to timestamps without a time zone for compatibility with PostgreSQL’s `TIMESTAMP` column.

---

# Español

# Documento de Decisiones Técnicas
## Pipeline ETL — DataMart S.A.S.

---

## 1. Diseño del modelo del repositorio analítico

El repositorio analítico fue diseñado con un esquema estrella simple compuesto por cuatro tablas:

- **`dim_product`** — dimensión de productos con código normalizado, nombre canónico, categoría y estado activo.
- **`dim_customer`** — dimensión de clientes con identificador y país.
- **`fact_transactions`** — tabla de hechos que centraliza tanto ventas como devoluciones, diferenciadas por la columna `transaction_type` (`SALE` o `RETURN`). Almacena el revenue bruto por línea de transacción.
- **`quality_rejects`** — tabla de log para registros rechazados durante la transformación, con el motivo del rechazo y la fuente de origen.

Este diseño permite responder todas las preguntas de negocio planteadas mediante joins simples entre la tabla de hechos y las dimensiones, y permite calcular ventas netas filtrando o agrupando por `transaction_type`.

---

## 2. Resolución de casos ambiguos

### 2.1 Transacciones sin customer_id

**Decisión:** se incluyeron en el análisis asignándoles el valor `ANONYMOUS` como identificador de cliente.

**Justificación:** excluirlas habría eliminado un volumen significativo de transacciones reales con revenue asociado, lo que distorsionaría los totales de ventas y el análisis por país. Al mantenerlas bajo un identificador especial, es posible segmentarlas y comparar su comportamiento frente a los clientes identificados, lo cual además responde directamente la pregunta de negocio número 5 del enunciado.

**Impacto documentado:** los clientes `ANONYMOUS` concentran una proporción relevante de las transacciones. Sus métricas de ticket promedio y revenue total son visibles en la consulta SQL de la pregunta 5.

---

### 2.2 Nombre canónico de productos

**Decisión:** se normalizó la descripción de cada producto a mayúsculas y sin espacios al inicio o al final (`str.upper().str.strip()`). En caso de múltiples variaciones para el mismo código de producto, se tomó la primera descripción encontrada después de la normalización.

**Justificación:** la normalización a mayúsculas elimina las variaciones de capitalización (`Candle Holder White`, `candle holder white`, `CANDLE HOLDER WHITE`) sin requerir lógica adicional de votación o frecuencia. Es una regla simple, aplicable de forma consistente a todos los registros y reproducible en cualquier ejecución del pipeline.

---

### 2.3 Duplicados entre las dos fuentes de datos

**Decisión:** se detectaron y eliminaron duplicados usando una clave compuesta de cuatro campos:

```
invoice + product_code + quantity + invoice_date
```

Ninguna fuente tiene prioridad sobre la otra. Cuando dos registros de distinta fuente coinciden en todos los campos de la clave, se conserva el primero en aparecer después de concatenar `source_1` (data.csv) seguida de `source_2` (online_retail_II.xlsx).

**Justificación:** una clave compuesta es más confiable que dar prioridad ciega a una fuente, ya que el solapamiento de fechas entre datasets no implica que todos los registros del período sean duplicados. Solo se descarta un registro cuando los cuatro campos coinciden exactamente, lo que indica con alta probabilidad que es la misma transacción reportada en ambas fuentes.

---

### 2.4 Registros con precio unitario menor o igual a cero

**Decisión:** los registros con `unit_price <= 0` fueron rechazados y registrados en la tabla `quality_rejects` con el motivo `"unit_price <= 0"`. No se incluyeron ni como ventas ni como devoluciones.

**Justificación:** el enunciado establece explícitamente que el precio unitario no puede ser cero ni negativo en una venta válida. Dado que no existe una regla de negocio que explique qué representa un precio negativo (podría ser un ajuste, un error de sistema o un descuento mal registrado), la decisión más segura es rechazarlos y dejar trazabilidad en el log para que el equipo de negocio los revise manualmente.

---

### 2.5 Transacciones con cantidad menor o igual a cero

**Decisión:** se separaron como devoluciones (`transaction_type = 'RETURN'`) y se almacenaron en la misma tabla `fact_transactions` junto a las ventas normales.

**Justificación:** mantenerlas en la misma tabla facilita el cálculo del revenue neto con una sola consulta de agregación filtrando por `transaction_type`, sin necesidad de joins entre tablas separadas. El signo de la cantidad y del revenue las identifica inequívocamente como devoluciones.

---

## 3. Garantía de idempotencia del DAG

El DAG es idempotente por diseño: ejecutarlo dos veces el mismo día con los mismos datos produce exactamente el mismo resultado en el repositorio analítico.

Esto se logra mediante una operación `DELETE` al inicio de la tarea `load`, que elimina todos los registros de `fact_transactions` cuya `transaction_date` corresponda a la fecha de ejecución del DAG (`context["ds"]`) antes de insertar los nuevos:

```sql
DELETE FROM fact_transactions
WHERE DATE(transaction_date) = '{{ ds }}'
```

Las dimensiones `dim_product` y `dim_customer` usan `ON CONFLICT DO NOTHING`, lo que garantiza que una segunda ejecución no duplique productos ni clientes ya existentes.

---

## 4. Decisión sobre transporte de datos entre tareas

**Decisión:** los DataFrames intermedios (ventas, devoluciones, rechazos) se guardan en archivos Parquet en `/opt/airflow/data/` en lugar de usar XCom de Airflow.

**Justificación:** el dataset combinado supera los 500.000 registros. Serializar ese volumen en JSON para XCom consumía más de 500 MB de memoria por tarea y causaba que el proceso recibiera SIGTERM por falta de recursos. Los archivos Parquet resuelven este problema al ser un formato columnar comprimido, y el directorio `/opt/airflow/data/` está montado como volumen compartido entre el scheduler y los workers, lo que garantiza que todas las tareas acceden a los mismos archivos.

---

## 5. Estrategia de categorización de productos

Dado que no se implementó la API opcional de productos, todos los productos se clasificaron bajo la categoría `UNCLASSIFIED` como valor por defecto, controlado por la Variable de Airflow `DEFAULT_CATEGORY`. Esta decisión está documentada y es reemplazable en una iteración futura conectando la API o cargando un archivo de mapeo estático de códigos a categorías.

---

## 6. Unificación de esquemas entre fuentes

Las dos fuentes tienen nombres de columna distintos para los mismos campos. Se aplicó un mapa de renombrado explícito en `transform.py`:

| Source 1 | Source 2 | Nombre canónico |
|---|---|---|
| InvoiceNo | Invoice | invoice |
| StockCode | StockCode | product_code |
| UnitPrice | Price | unit_price |
| CustomerID | Customer ID | customer_id |
| InvoiceDate | InvoiceDate | invoice_date |

Todos los campos de fecha fueron estandarizados a UTC y luego convertidos a timestamp sin timezone para compatibilidad con la columna `TIMESTAMP` de PostgreSQL.