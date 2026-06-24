# DataMart S.A.S. — Pipeline ETL con Apache Airflow

## Descripción de la Empresa
DataMart S.A.S. es una empresa colombiana de comercio electrónico fundada en 2018. Cuenta con operaciones internacionales en tres países: **Colombia, México y Perú**.

## Modelo de Negocio
La empresa se dedica a la comercialización minorista multicanal y multicategoría a través de:
* **Canales de venta:** Tienda en línea propia y distribuidores minoristas aliados.
* **Catálogo de productos:** Más de 3,000 referencias activas.
* **Categorías:** Electrónica, Hogar, Ropa, Deportes y Papelería.

## Desafíos y Problemáticas Actuales
A pesar de experimentar un crecimiento del **40% en transacciones durante 2023**, la operación analítica se encuentra paralizada debido a los siguientes problemas técnicos:

* **Dispersión de almacenamiento:** Los datos de ventas se generan diariamente en archivos planos dentro del servidor de producción.
* **Deuda técnica:** El catálogo de productos se administra en un sistema legado que carece de una estructura analítica.
* **Calidad de datos:** Los registros de devoluciones y cancelaciones están mezclados con las ventas normales sin ninguna separación.
* **Falta de estandarización:** El análisis global está bloqueado porque las fuentes de información manejan diferentes monedas y formatos de fecha.

### Impacto en el Negocio
* **Finanzas:** El cierre de reportes mensuales se retrasa entre 3 y 5 días por tareas de consolidación manual.
* **Producto:** Incapacidad para identificar cuáles referencias de productos están generando pérdidas.
* **Dirección:** Bloqueo estratégico al no poder comparar el desempeño comercial entre los tres países operacionales.

---

## Requisitos previos
- Docker Desktop instalado y corriendo
- Git
- Puerto 8080 libre en tu máquina

## Levantar el entorno

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd DataMartSAS

# 2. Crear el archivo de variables de entorno
cp .env.example .env
# Edita .env con las credenciales reales 

# 3. Levantar todos los servicios
docker-compose up

# Espera ver: "Serving on http://0.0.0.0:8080"
# Tarda entre 5 y 10 minutos la primera vez
```

## Verificar que todo quedó bien

```bash
# 1. Webserver responde
curl http://localhost:8080/health

# 2. Verificar connections y variables
docker exec datamartsas_airflow-webserver_1 airflow connections get postgres_dw
docker exec datamartsas_airflow-webserver_1 airflow variables get SOURCE_FILE_1
docker exec datamartsas_airflow-webserver_1 airflow variables get SOURCE_FILE_2

# 3. Entrar a la UI
# http://localhost:8080
# Usuario: el que definiste en AIRFLOW_ADMIN_USER
# Contraseña: el que definiste en AIRFLOW_ADMIN_PASSWORD
```

## Ejecutar el pipeline

1. Abre http://localhost:8080
2. Busca el DAG `datamart_etl`
3. Actívalo con el toggle
4. Haz clic en "Trigger DAG" para ejecutarlo manualmente
5. Verifica que las 4 tareas queden en verde:
   - `extract_source_1`
   - `extract_source_2`
   - `transform`
   - `load`

## Verificar datos en el DWH

Conéctate al servidor PostgreSQL (DBeaver, psql):

```
Host:     <POSTGRES_HOST del .env>
Puerto:   <POSTGRES_PORT del .env>
Usuario:  <POSTGRES_USER del .env>
Base:     <POSTGRES_DB del .env>
```

```sql
-- Verificar que llegaron datos
SELECT COUNT(*) FROM fact_transactions;
SELECT COUNT(*) FROM dim_product;
SELECT COUNT(*) FROM dim_customer;
SELECT COUNT(*) FROM quality_rejects;
```

## Estructura del repositorio

```
DataMartSAS/
├── dags/
│   └── datamart_etl_dag.py   # DAG principal
├── scripts/
│   ├── extract.py            # Extracción de fuentes
│   ├── transform.py          # Limpieza y reglas de negocio
│   └── load.py               # Carga al DWH
├── sql/
│   ├── create_tables.sql     # DDL del repositorio analítico
│   └── queries_validation.sql # Consultas de las preguntas de negocio
├── data/
│   ├── data.csv              # Fuente 1 — transacciones
│   └── online_retail_II.xlsx # Fuente 2 — historial
├── docker-compose.yml
├── .env.example
└── README.md
```