import os
import sys
import argparse
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import s3fs

# Thêm đường dẫn để python có thể tìm thấy job_matcher_app khi chạy trong container airflow
sys.path.append("/opt/airflow/dags")
sys.path.append("/opt/airflow")
sys.path.append("/opt")

def main():
    parser = argparse.ArgumentParser(description="Silver to Gold NLP Job")
    parser.add_argument('--execution_date', type=str, required=True, help='Execution date YYYY-MM-DD')
    args, unknown = parser.parse_known_args()
    execution_date_str = args.execution_date

    date_obj = datetime.strptime(execution_date_str, "%Y-%m-%d")
    year_str = date_obj.strftime("%Y")
    month_str = date_obj.strftime("%m")
    day_str = date_obj.strftime("%d")

    # Connect to MinIO
    s3 = s3fs.S3FileSystem(
        key=os.getenv("MINIO_ACCESS_KEY", "ROOTUSER"),
        secret=os.getenv("MINIO_SECRET_KEY", "1234567890"),
        client_kwargs={'endpoint_url': 'http://minio:9000'},
        use_ssl=False
    )
    
    silver_path = f"silver-layer/topcv/job_detail/year={year_str}/month={month_str}/day={day_str}"
    
    try:
        if not s3.exists(silver_path):
            print(f"Silver path {silver_path} does not exist.")
            return

        dataset = pq.ParquetDataset(silver_path, filesystem=s3)
        table = dataset.read()
        df = table.to_pandas()
    except Exception as e:
        print(f"Failed to read from silver layer: {e}")
        return

    print(f"Loaded {len(df)} records from Silver layer.")
    if len(df) == 0:
        return

    # Khởi tạo mô hình NER và SkillTrie từ backend (biến toàn cục sẽ được load khi import)
    os.environ["SKILL_EXTRACTOR_MODE"] = os.getenv("SKILL_EXTRACTOR_MODE", "ner_skilltrie")
    
    try:
        from job_matcher_app.skill_extraction_worker import extract_job_skills
    except ImportError as e:
        print(f"Không thể import module backend: {e}")
        return

    def extract_skills_from_row(row):
        try:
            job_mock = {
                "title": str(row.get("detail_title", "")),
                "description": str(row.get("desc_mota", "")),
                "requirement": str(row.get("desc_yeucau", ""))
            }
            # skill_names, extraction_source
            skill_names, _ = extract_job_skills(job_mock)
            return skill_names
        except Exception as e:
            print(f"Error extracting skills: {e}")
            return []

    # Áp dụng trích xuất cho mỗi dòng
    print("Bắt đầu trích xuất kỹ năng bằng mô hình NER / SkillTrie...")
    df["extracted_skills"] = df.apply(extract_skills_from_row, axis=1)
    
    gold_path = f"gold-layer/topcv/job_detail/year={year_str}/month={month_str}/day={day_str}"
    print(f"Writing {len(df)} records to Gold layer: {gold_path}")
    
    table_out = pa.Table.from_pandas(df)
    
    import pyarrow.dataset as ds
    ds.write_dataset(
        data=table_out,
        base_dir=gold_path,
        format="parquet",
        filesystem=s3,
        existing_data_behavior="overwrite_or_ignore"
    )

    print("Silver to Gold NLP completed.")

if __name__ == "__main__":
    main()
