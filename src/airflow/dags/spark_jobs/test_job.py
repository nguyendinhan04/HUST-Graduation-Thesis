from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructType, StructField
from pyspark.sql.functions import lit


def main():
    spark = SparkSession.builder \
        .appName("Spark Job Example") \
        .config("spark.jars", "/opt/airflow/jars/postgresql-42.2.18.jar") \
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



    df.show()
    spark.stop()

if __name__ == "__main__":
    main()