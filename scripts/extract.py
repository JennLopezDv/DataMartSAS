import pandas as pd
from airflow.hooks.base import BaseHook
from airflow.models import Variable
import logging

logger = logging.getLogger(__name__)

def extract_source_1(**context):
    """Extrae data.csv — transacciones UK"""
    filepath = Variable.get("SOURCE_FILE_1")
    
    logger.info(f"Leyendo fuente 1: {filepath}")
    df = pd.read_csv(
        filepath,
        encoding="ISO-8859-1",   # Caracteres latinos
        dtype=str                  # leer todo como string, transformar después
    )
    logger.info(f"Fuente 1: {len(df)} filas, {df.columns.tolist()}")
    
    # Guardar para la siguiente tarea
    df.to_parquet("/opt/airflow/data/raw_source_1.parquet", index=False)
    return f"source_1: {len(df)} filas"

def extract_source_2(**context):
    """Extrae online_retail_II.xlsx — historial extendido"""
    filepath = Variable.get("SOURCE_FILE_2")
    
    logger.info(f"Leyendo fuente 2: {filepath}")
    df = pd.read_excel(
        filepath,
        dtype=str,
        engine="openpyxl"
    )
    logger.info(f"Fuente 2: {len(df)} filas, {df.columns.tolist()}")
    
    df.to_parquet("/opt/airflow/data/raw_source_2.parquet", index=False)
    return f"source_2: {len(df)} filas"