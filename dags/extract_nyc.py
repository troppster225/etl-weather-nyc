# flows/extract_nyc.py
from prefect import flow, task
import httpx, pathlib, pendulum, subprocess, os

RAW_DIR = pathlib.Path("/tmp/taxi")

@task(retries=3, log_prints=True)
def download_latest() -> pathlib.Path:
    ym = pendulum.now("UTC").subtract(months=1).format("YYYY-MM")
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{ym}.parquet"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fp = RAW_DIR / url.split("/")[-1]
    if not fp.exists():
        fp.write_bytes(httpx.get(url).content)
        print(f"✔ Downloaded {fp.name}")
    else:
        print(f"↷ File already present, skipping download")
    return fp

@task
def upload_to_minio(fp: pathlib.Path):
    bucket_path = f"local/raw/taxi/{fp.name}"
    subprocess.run(["mc", "cp", str(fp), bucket_path], check=True)
    print(f"↑ Uploaded to s3://raw/taxi/{fp.name}")

@flow
def extract_nyc():
    upload_to_minio(download_latest())

if __name__ == "__main__":
    extract_nyc()