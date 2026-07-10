from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructType, StructField, FloatType,MapType, IntegerType
from pyspark.sql.functions import lit, to_date
from pyspark.sql import functions as F
import argparse
import re
import ast


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

    # Tìm tất cả số (bao gồm cả số thập phân)
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

    return numbers[0]

def parse_general_info_py(info_str):
    if info_str is None or info_str.strip() == "":
        return (None, None, None, None)
    try:
        # literal_eval giúp chuyển chuỗi '{...}' thành dict Python an toàn
        info_dict = ast.literal_eval(info_str)
        if isinstance(info_dict, dict):
            # Đảm bảo tất cả key/value đều là string để khớp với MapType<String, String>
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
        for item in box_list:
            if isinstance(item, dict):
                parse_box_dict.update({item.get("box_title"): item.get("categories")})
        return (
            parse_box_dict.get("Danh mục Nghề liên quan"),
            parse_box_dict.get("Kỹ năng cần có"),
            parse_box_dict.get("Khu vực"),
            parse_box_dict.get("Kỹ năng nên có")
        )
    except (ValueError, SyntaxError):
        return (None, None, None, None)


def main():
    parser = argparse.ArgumentParser(description="Spark Job Example")
    parser.add_argument('--execution_date', type=str, required=False, help='Execution date passed from Luigi')
    args, unknown = parser.parse_known_args()
    execution_date = args.execution_date

    # Nếu không có --execution_date, thử lấy positional argument
    if not execution_date and len(unknown) > 0:
        execution_date = unknown[0]


    jars_path = "/opt/airflow/jars/postgresql-42.2.18.jar,/opt/airflow/jars/aws-java-sdk-bundle-1.12.262.jar,/opt/airflow/jars/hadoop-aws-3.3.4.jar"

    spark = SparkSession.builder \
        .appName("Spark Job Cleaning") \
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

    DEFAULTS = {
        "PG_HOST": "postgres2",  # Docker service name
        "PG_PORT": 5432,
        "PG_DATABASE": "job_db",
        "PG_USER": "airflow",
        "PG_PASSWORD": "airflow"
    }

    df = spark.read \
        .format("jdbc") \
        .option("url", f"jdbc:postgresql://{DEFAULTS['PG_HOST']}:{DEFAULTS['PG_PORT']}/{DEFAULTS['PG_DATABASE']}") \
        .option("dbtable", "detail_jobs") \
        .option("user", DEFAULTS['PG_USER']) \
        .option("password", DEFAULTS['PG_PASSWORD']) \
        .option("driver", "org.postgresql.Driver") \
        .load()

    # Chuyển datetime về date để so sánh
    df = df.filter(to_date(df["datetime"]) == lit(execution_date))

    valid_df = df.filter(df["desc_mota"].isNotNull() & df["desc_yeucau"].isNotNull() & df["desc_quyenloi"].isNotNull())
    null_df = df.filter(df["desc_mota"].isNull() | df["desc_yeucau"].isNull() | df["desc_quyenloi"].isNull())

    valid_df.show(5, truncate=False)
    # Parse salary
    salary_schema = StructType([
        StructField("min_salary", FloatType(), True),
        StructField("max_salary", FloatType(), True),
        StructField("currency", StringType(), True)
    ])
    parse_salary_udf = F.udf(parse_salary_py, salary_schema)

    valid_df = valid_df.withColumn("salary_struct", parse_salary_udf(F.col("detail_salary"))) \
        .select(
        "*",
        "salary_struct.*"
    ) \
        .drop("salary_struct")

    # Parse experience
    parse_experience_udf = F.udf(parse_experience, FloatType())
    valid_df = valid_df.withColumn("experience_years", parse_experience_udf(F.col("detail_experience")))

    # parse general info
    general_info_schema = StructType([
        StructField("Cấp bậc", StringType(), True),
        StructField("Học vấn", StringType(), True),
        StructField("Số lượng tuyển", StringType(), True),
        StructField("Hình thức làm việc", StringType(), True),
    ])
    parse_info_udf = F.udf(parse_general_info_py, general_info_schema)
    valid_df = valid_df.withColumn("parsed_general_info", parse_info_udf(F.col("general_info")))
    valid_df = valid_df.select("*", "parsed_general_info.*").drop("parsed_general_info", "general_info")

    # Parse working time
    parse_working_time_udf = F.udf(parse_working_time, IntegerType())
    valid_df = valid_df.withColumn("working_days_per_week", parse_working_time_udf(F.col("working_times"))) \
        .drop("working_times")

    # Parse box category
    box_category_schema = StructType([
        StructField("Danh mục Nghề liên quan", StringType(), True),
        StructField("Kỹ năng cần có", StringType(), True),
        StructField("Khu vực", StringType(), True),
        StructField("Kỹ năng nên có", StringType(), True),
    ])

    parse_box_udf = F.udf(parse_box_category, box_category_schema)
    valid_df = valid_df.withColumn("parsed_box_category", parse_box_udf(F.col("box_categories")))
    valid_df = valid_df.select("*", "parsed_box_category.*").drop("parsed_box_category", "box_categories")


    valid_df = valid_df.withColumn(
        "Số lượng tuyển",
        F.regexp_extract(F.col("Số lượng tuyển"), r"(\d+)", 1).cast(IntegerType())
    )


    valid_df = valid_df.withColumn("parse_detail_title", F.lower(F.col("detail_title")))
    valid_df = valid_df.withColumn("parse_desc_mota", F.lower(F.col("desc_mota")))
    valid_df = valid_df.withColumn("parse_desc_yeucau", F.lower(F.col("desc_yeucau")))
    valid_df = valid_df.withColumn("parse_desc_quyenloi", F.lower(F.col("desc_quyenloi")))


    valid_df.show(5, truncate=False)

    # write to minio, partition by datetime
    # valid_df.write \
    #     .mode("append") \
    #     .parquet(f"s3a://silver-layer/cleaned_jobs/datetime={execution_date}")


    valid_df.write \
        .mode("append") \
        .parquet(f"s3a://silver-layer/cleaned_jobs/datetime=test_cleaning")
    
    spark.stop()

if __name__ == "__main__":
    main()