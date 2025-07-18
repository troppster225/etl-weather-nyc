# flows/load_taxi_raw.py
from prefect import flow, task
import boto3, psycopg2, os, io, pandas as pd
from smart_open import open as sopen   # pip install smart_open

S3 = boto3.client(
    "s3",
    endpoint_url="http://minio:9000",
    aws_access_key_id=os.environ["MINIO_ROOT_USER"],
    aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
)

@task(log_prints=True)
def copy_latest_to_pg():
    obj = S3.list_objects_v2(Bucket="raw", Prefix="taxi/")["Contents"][-1]["Key"]
    with sopen(f"s3://raw/{obj}", transport_params={"client": S3}) as f:
        df = pd.read_parquet(f)
    conn = psycopg2.connect(
        host="postgres",
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS nyc_taxi_raw
        (like staging_template INCLUDING DEFAULTS)
        """
    )
    # simple incremental upsert
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    cur.copy_expert(
        """
        COPY nyc_taxi_raw FROM STDIN WITH CSV
        """,
        buffer,
    )
    conn.commit()
    conn.close()
    print(f"↓ Loaded {len(df):,} rows into nyc_taxi_raw")

@flow
def load_taxi_raw():
    copy_latest_to_pg()

if __name__ == "__main__":
    load_taxi_raw()
