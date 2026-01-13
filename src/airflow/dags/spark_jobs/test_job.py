from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructType, StructField
from pyspark.sql.functions import lit

jars = "/opt/airflow/jars/hadoop-aws-3.3.4.jar,/opt/airflow/jars/aws-java-sdk-bundle-1.12.262.jar,/opt/airflow/jars/postgresql-42.2.18.jar,/opt/airflow/jars/delta-spark_2.12-3.3.2.jar,/opt/airflow/jars/delta-storage-3.3.2.jar"


def main():
    spark = SparkSession.builder \
        .appName("Spark Job Example") \
        .config("spark.jars", jars) \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.databricks.delta.retentionDurationCheck.enabled", "false") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "ROOTUSER") \
        .config("spark.hadoop.fs.s3a.secret.key", "1234567890") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.sql.shuffle.partitions", "4") \
        .config("spark.default.parallelism", "4") \
        .config("spark.executor.cores", "1") \
        .config("spark.dynamicAllocation.enabled", "false") \
        .getOrCreate()

    DEFAULTS = {
        "PG_HOST": "postgres",  # Docker service name
        "PG_PORT": 5432,
        "PG_DATABASE": "job_db",
        "PG_USER": "airflow",
        "PG_PASSWORD": "airflow"
    }

    # df = spark.read \
    #     .format("jdbc") \
    #     .option("url", f"jdbc:postgresql://{DEFAULTS['PG_HOST']}:{DEFAULTS['PG_PORT']}/{DEFAULTS['PG_DATABASE']}") \
    #     .option("dbtable", "jobs") \
    #     .option("user", DEFAULTS['PG_USER']) \
    #     .option("password", DEFAULTS['PG_PASSWORD']) \
    #     .option("driver", "org.postgresql.Driver") \
    #     .load()


    # df.write \
    #     .format("parquet") \
    #     .mode("overwrite") \
    #     .save("s3a://silver-layer/test")


    df = spark.read \
        .format("parquet") \
        .load("s3a://silver-layer/test")
    df.show()

    # df = spark.read \
    #     .format("delta") \
    #     .load("s3a://delta/jobs_delta_table")
    
   

    # df.show()
    spark.stop()

if __name__ == "__main__":
    main()