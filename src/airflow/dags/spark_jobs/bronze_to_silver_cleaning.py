from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructType, StructField, FloatType, MapType, IntegerType
from pyspark.sql.functions import lit, to_date
from pyspark.sql import functions as F
import argparse
import re
import ast
from datetime import datetime

def parse_salary_py(salary_str):
    if salary_str is None:
        return (None, None, None)

    salary_str = salary_str.replace(",", "").strip()
    if "Thỏa thuận" in salary_str:
        return (None, None, None)

    currency = None
    if "USD" in salary_str:
        currency = "USD"
    elif "triệu" in salary_str:
        currency = "trieu VND"

    numbers = [float(s) for s in re.findall(r'\d+(?:\.\d+)?', salary_str)]

    min_salary, max_salary = None, None

    if "Từ" in salary_str and len(numbers) >= 1:
        min_salary = numbers[0]
    elif "Tới" in salary_str and len(numbers) >= 1:
        max_salary = numbers[0]
    elif "-" in salary_str and len(numbers) >= 2:
        min_salary = numbers[0]
        max_salary = numbers[1]

    return (min_salary, max_salary, currency)


def parse_experience(exp_str):
    if (exp_str is None) or (not isinstance(exp_str, str)):
        return None

    exp_str = exp_str.replace("năm", "").strip()
    if "Không yêu cầu" in exp_str:
        return 0

    if "Dưới 1" in exp_str:
        return 0.5

    if "Trên 5" in exp_str:
        return 7

    numbers = [float(s) for s in re.findall(r'\d+(?:\.\d+)?', exp_str)]
    if not numbers:
        return None
    return numbers[0]

def parse_general_info_py(info_str):
    if info_str is None or info_str.strip() == "":
        return (None, None, None, None)
    try:
        info_dict = ast.literal_eval(info_str)
        if isinstance(info_dict, dict):
            parsed_info_dict =  {str(k): str(v) for k, v in info_dict.items()}
            return (
                parsed_info_dict.get("Cấp bậc"),
                parsed_info_dict.get("Học vấn"),
                parsed_info_dict.get("Số lượng tuyển"),
                parsed_info_dict.get("Hình thức làm việc")
            )
        return (None, None, None, None)
    except (ValueError, SyntaxError):
        return (None, None, None, None)

def parse_working_time(wt_str):
    if (wt_str is None or not isinstance(wt_str, str)):
        return None

    wt_str = wt_str.strip().lower()
    if "thứ 2 - thứ 6" in wt_str:
        return 5
    if "thứ 2 - thứ 7" in wt_str:
        return 6
    if "thứ 2 - chủ nhật" in wt_str:
        return 7
    return "Other"

def parse_box_category(box_str):
    if box_str is None or box_str.strip() == "":
        return (None, None, None, None)
    try:
        box_list = ast.literal_eval(box_str)
        parse_box_dict = {}
        if isinstance(box_list, list):
            for item in box_list:
                if isinstance(item, dict):
                    parse_box_dict.update({item.get("box_title"): item.get("categories")})
            return (
                str(parse_box_dict.get("Danh mục Nghề liên quan", "")),
                str(parse_box_dict.get("Kỹ năng cần có", "")),
                str(parse_box_dict.get("Khu vực", "")),
                str(parse_box_dict.get("Kỹ năng nên có", ""))
            )
        return (None, None, None, None)
    except (ValueError, SyntaxError):
        return (None, None, None, None)


def main():
    parser = argparse.ArgumentParser(description="Spark Job Bronze to Silver")
    parser.add_argument('--execution_date', type=str, required=True, help='Execution date YYYY-MM-DD')
    args, unknown = parser.parse_known_args()
    execution_date_str = args.execution_date

    # Lấy year, month, day từ execution_date
    date_obj = datetime.strptime(execution_date_str, "%Y-%m-%d")
    year_str = date_obj.strftime("%Y")
    month_str = date_obj.strftime("%m")
    day_str = date_obj.strftime("%d")

    jars_path = "/opt/airflow/jars/postgresql-42.2.18.jar,/opt/airflow/jars/aws-java-sdk-bundle-1.12.262.jar,/opt/airflow/jars/hadoop-aws-3.3.4.jar"

    spark = SparkSession.builder \
        .appName("Bronze to Silver Job Cleaning") \
        .config("spark.jars", jars_path) \
        .config("spark.driver.extraClassPath", jars_path) \
        .config("spark.executor.extraClassPath", jars_path) \
        .config("spark.driver.extraJavaOptions", "--add-opens=java.base/java.nio=ALL-UNNAMED") \
        .config("spark.executor.extraJavaOptions", "--add-opens=java.base/java.nio=ALL-UNNAMED") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "ROOTUSER") \
        .config("spark.hadoop.fs.s3a.secret.key", "1234567890") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .getOrCreate()

    # Đường dẫn file Bronze Layer theo partition ngày
    bronze_path = f"s3a://bronze-layer/topcv/job_detail/year={year_str}/month={month_str}/day={day_str}/*.jsonl"
    
    try:
        df = spark.read.json(bronze_path)
    except Exception as e:
        print(f"Không có dữ liệu cho ngày {execution_date_str}: {e}")
        spark.stop()
        return

    print(f"Tổng số bản ghi ban đầu: {df.count()}")

    # 1. Loại bỏ bản ghi trùng lặp theo url_hash
    df = df.dropDuplicates(["url_hash"])
    print(f"Tổng số bản ghi sau khi deduplicate: {df.count()}")

    # 2. Loại bỏ các record thiếu trường thông tin quan trọng
    # crawl_job_detail_task trả về detail_title, desc_yeucau, desc_mota
    if "detail_title" in df.columns and "desc_yeucau" in df.columns and "desc_mota" in df.columns:
        valid_df = df.filter(df["detail_title"].isNotNull() & df["desc_yeucau"].isNotNull() & df["desc_mota"].isNotNull())
    else:
        print("Dữ liệu không có đủ các cột bắt buộc: detail_title, desc_yeucau, desc_mota")
        spark.stop()
        return

    print(f"Tổng số bản ghi sau khi xoá nulls: {valid_df.count()}")

    # 3. Làm sạch dữ liệu (parse fields) - Tương tự data_cleaning.py
    if "detail_salary" in valid_df.columns:
        salary_schema = StructType([
            StructField("min_salary", FloatType(), True),
            StructField("max_salary", FloatType(), True),
            StructField("currency", StringType(), True)
        ])
        parse_salary_udf = F.udf(parse_salary_py, salary_schema)
        valid_df = valid_df.withColumn("salary_struct", parse_salary_udf(F.col("detail_salary"))) \
            .select("*", "salary_struct.*") \
            .drop("salary_struct")

    if "detail_experience" in valid_df.columns:
        parse_experience_udf = F.udf(parse_experience, FloatType())
        valid_df = valid_df.withColumn("experience_years", parse_experience_udf(F.col("detail_experience")))

    if "general_info" in valid_df.columns:
        general_info_schema = StructType([
            StructField("Cấp bậc", StringType(), True),
            StructField("Học vấn", StringType(), True),
            StructField("Số lượng tuyển", StringType(), True),
            StructField("Hình thức làm việc", StringType(), True),
        ])
        parse_info_udf = F.udf(parse_general_info_py, general_info_schema)
        valid_df = valid_df.withColumn("parsed_general_info", parse_info_udf(F.col("general_info")))
        valid_df = valid_df.select("*", "parsed_general_info.*").drop("parsed_general_info", "general_info")
        
        valid_df = valid_df.withColumn(
            "Số lượng tuyển",
            F.regexp_extract(F.col("Số lượng tuyển"), r"(\d+)", 1).cast(IntegerType())
        )

    if "working_times" in valid_df.columns:
        parse_working_time_udf = F.udf(parse_working_time, IntegerType())
        valid_df = valid_df.withColumn("working_days_per_week", parse_working_time_udf(F.col("working_times"))) \
            .drop("working_times")

    if "box_categories" in valid_df.columns:
        box_category_schema = StructType([
            StructField("Danh mục Nghề liên quan", StringType(), True),
            StructField("Kỹ năng cần có", StringType(), True),
            StructField("Khu vực", StringType(), True),
            StructField("Kỹ năng nên có", StringType(), True),
        ])
        parse_box_udf = F.udf(parse_box_category, box_category_schema)
        valid_df = valid_df.withColumn("parsed_box_category", parse_box_udf(F.col("box_categories")))
        valid_df = valid_df.select("*", "parsed_box_category.*").drop("parsed_box_category", "box_categories")

    # Chuẩn hoá lower case
    for col_name in ["detail_title", "desc_mota", "desc_yeucau", "desc_quyenloi"]:
        if col_name in valid_df.columns:
            valid_df = valid_df.withColumn(f"parse_{col_name}", F.lower(F.col(col_name)))

    valid_df.show(5, truncate=False)

    # 4. Ghi output xuống Silver Layer
    silver_output_path = f"s3a://silver-layer/topcv/job_detail/year={year_str}/month={month_str}/day={day_str}"
    print(f"Ghi dữ liệu vào Silver Layer: {silver_output_path}")

    valid_df.write \
        .mode("overwrite") \
        .parquet(silver_output_path)
    
    print("ETL hoàn tất thành công.")
    spark.stop()

if __name__ == "__main__":
    main()
