from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructType, StructField
from pyspark.sql.functions import lit
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Spark Job Example")
    parser.add_argument('--execution_date', type=str, required=False, help='Execution date passed from Luigi')
    args, unknown = parser.parse_known_args()
    execution_date = args.execution_date

    # Nếu không có --execution_date, thử lấy positional argument
    if not execution_date and len(unknown) > 0:
        execution_date = unknown[0]

    spark = SparkSession.builder \
        .appName("Spark Job Example") \
        .config("spark.jars", "/opt/airflow/jars/postgresql-42.2.18.jar") \
        .config("spark.driver.extraClassPath", "/opt/airflow/jars/postgresql-42.2.18.jar") \
        .config("spark.executor.extraClassPath", "/opt/airflow/jars/postgresql-42.2.18.jar") \
        .config("spark.driver.extraJavaOptions", "--add-opens=java.base/java.nio=ALL-UNNAMED") \
        .config("spark.executor.extraJavaOptions", "--add-opens=java.base/java.nio=ALL-UNNAMED") \
        .getOrCreate()

    DEFAULTS = {
        "PG_HOST": "postgres",  # Docker service name
        "PG_PORT": 5432,
        "PG_DATABASE": "job_db",
        "PG_USER": "airflow",
        "PG_PASSWORD": "airflow"
    }

    df = spark.read \
        .format("jdbc") \
        .option("url", f"jdbc:postgresql://{DEFAULTS['PG_HOST']}:{DEFAULTS['PG_PORT']}/{DEFAULTS['PG_DATABASE']}") \
        .option("dbtable", "jobs") \
        .option("user", DEFAULTS['PG_USER']) \
        .option("password", DEFAULTS['PG_PASSWORD']) \
        .option("driver", "org.postgresql.Driver") \
        .load()

    # Log execution_date for debugging
    if execution_date:
        print(f"Execution date received: {execution_date}")
    else:
        print("No execution_date provided.")
    spark.stop()

if __name__ == "__main__":
    main()