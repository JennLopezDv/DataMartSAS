# DataMart S.A.S. — ETL Pipeline with Apache Airflow

## Company Description
DataMart S.A.S. is a Colombian e-commerce company founded in 2018. It has international operations in three countries: **Colombia, Mexico, and Peru**.

## Business Model
The company is engaged in multichannel, multi-category retail sales through:
* **Sales Channels:** Its own online store and partner retailers.
* **Product Catalog:** More than 3,000 active SKUs.
* **Categories:** Electronics, Home Goods, Clothing, Sports, and Stationery.

## Current Challenges and Issues
Despite experiencing **40% growth in transactions during 2023**, analytics operations have come to a standstill due to the following technical issues:

* **Scattered storage:** Sales data is generated daily in flat files on the production server.
* **Technical debt:** The product catalog is managed in a legacy system that lacks an analytical structure.
* **Data quality:** Records of returns and cancellations are mixed with normal sales without any separation.
* **Lack of standardization:** Overall analysis is blocked because data sources use different currencies and date formats.

### Business Impact
* **Finance:** The closing of monthly reports is delayed by 3 to 5 days due to manual consolidation tasks.
* **Product:** Inability to identify which product SKUs are generating losses.
* **Management:** Strategic bottleneck due to the inability to compare business performance across the three countries where the company operates.

---


## Prerequisites
- Docker Desktop installed and running
- Git
- Port 8080 must be free on your machine

## Setting Up the Environment

```bash
# 1. Clone the repository
git clone <repo-url>
cd DataMartSAS

# 2. Create the environment variables file
cp .env.example .env
# Edit .env with the actual credentials.

# 3. Start all services
docker-compose up

# You should see: “Serving on http://0.0.0.0:8080”
# Takes between 5 and 10 minutes the first time
```

## Verify that everything is working correctly

```bash
# 1. Web server is responding
curl http://localhost:8080/health

# 2. Verify connections and variables
docker exec datamartsas_airflow-webserver_1 airflow connections get postgres_dw
docker exec datamartsas_airflow-webserver_1 airflow variables get SOURCE_FILE_1
docker exec datamartsas_airflow-webserver_1 airflow variables get SOURCE_FILE_2

# 3. Log in to the UI
# http://localhost:8080
# Username: the one you defined in AIRFLOW_ADMIN_USER
# Password: the one you defined in AIRFLOW_ADMIN_PASSWORD
```

## Run the pipeline

1. Open http://localhost:8080
2. Find the DAG `datamart_etl`
3. Enable it using the toggle
4. Click “Trigger DAG” to run it manually
5. Verify that all 4 tasks are green:
   - `extract_source_1`
   - `extract_source_2`
   - `transform`
   - `load`

## Verify data in the DWH

Connect to the TL’s PostgreSQL server using any client (DBeaver, psql):

```
Host:     <POSTGRES_HOST from .env>
Port:   <POSTGRES_PORT from .env>
Username: <POSTGRES_USER from .env>
Database: <POSTGRES_DB from .env>
```

```sql
-- Verify that data has been loaded
SELECT COUNT(*) FROM fact_transactions;
SELECT COUNT(*) FROM dim_product;
SELECT COUNT(*) FROM dim_customer;
SELECT COUNT(*) FROM quality_rejects;
```

## Repository Structure

```
DataMartSAS/
├── dags/
│   └── datamart_etl_dag.py   # Main DAG
├── scripts/
│   ├── extract.py            # Source extraction
│   ├── transform.py          # Data cleansing and business rules
│   └── load.py               # Load into the DWH
├── sql/
│   ├── create_tables.sql     # DDL for the analytics repository
│   └── queries_validation.sql # Queries for business questions
├── data/
│   ├── data.csv              # Source 1 — transactions
│   └── online_retail_II.xlsx # Source 2 — history
├── docker-compose.yml
├── .env.example
└── README.md
```

Translated with DeepL.com (free version)

