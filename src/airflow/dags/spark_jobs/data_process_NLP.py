from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructType, StructField, FloatType,MapType, IntegerType
from pyspark.sql.functions import lit, to_date
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType
from pyspark.sql.functions import udf,col
from pyspark.sql import Row
from underthesea import word_tokenize
from pyspark.ml.feature import IDF
from pyspark.ml.feature import Tokenizer,PCA
from pyspark.ml.feature import CountVectorizer
from pyspark.ml.feature import IDF
from pyspark.ml import Pipeline
import argparse
import psycopg2
from psycopg2.extras import execute_batch
import re
import ast

jars_path = "/opt/airflow/jars/postgresql-42.2.18.jar,/opt/airflow/jars/aws-java-sdk-bundle-1.12.262.jar,/opt/airflow/jars/hadoop-aws-3.3.4.jar"

def vn_tokenize(text):
    return word_tokenize(text, format="list")

def vec_to_list(v):
    return v.toArray().tolist()

def pad_vector(vec, target_size=2500):
    """Pad vector to target_size with zeros"""
    vec_list = vec.toArray().tolist()
    if len(vec_list) < target_size:
        vec_list.extend([0.0] * (target_size - len(vec_list)))
    return vec_list[:target_size]




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
        .appName("Spark Job Example") \
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
        .config("spark.sql.shuffle.partitions", "5") \
        .config("spark.default.parallelism", "5") \
        .getOrCreate()
    
    DEFAULTS = {
        "PG_HOST": "postgres",  # Docker service name
        "PG_PORT": 5432,
        "PG_DATABASE": "job_db",
        "PG_USER": "airflow",
        "PG_PASSWORD": "airflow"
    }

    job_df = spark.read.parquet(r"s3a://silver-layer/cleaned_jobs/datetime=test_cleaning")
    
    job_df = job_df.withColumn("desc_combined", F.concat_ws(" ", F.col("parse_desc_mota"), F.col("parse_desc_yeucau"), F.col("parse_desc_quyenloi")))
    
    # ------------------------------------
    tokenizer = Tokenizer(inputCol="desc_combined", outputCol="tokens")
    cv = CountVectorizer(
    inputCol="tokens",
    outputCol="tf_features",
    vocabSize=2500,
    minDF=2
    )
    idf = IDF(inputCol="tf_features", outputCol="tfidf_features")

    svd = PCA(
    k=200,
    inputCol="tfidf_features",
    outputCol="embedding"
    )


    pipeline = Pipeline(stages=[tokenizer, cv, idf, svd])

    model = pipeline.fit(job_df)
    job_vec_df = model.transform(job_df)
    
    # Select only needed columns and persist to save memory
    df_vec = job_vec_df.select("id", "embedding")

    # # For database insertion, process in batches to avoid OOM

    df_out = df_vec.select(
        col("id"),
        col("embedding")  # pgvector nhận dạng array text
    )


    df_out.write \
        .format("jdbc") \
        .option("url", "jdbc:postgresql://postgres:5432/job_db") \
        .option("dbtable", "job_tfidf_embedding") \
        .option("user", "airflow") \
        .option("password", "airflow") \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()




    # -----------------------------------------------------------
    # conn = psycopg2.connect(
    # host="postgres",
    # port=5432,
    # dbname="job_db",
    # user="airflow",
    # password="airflow"
    # )

    # sql = """
    # INSERT INTO job_tfidf_embedding (id, embedding)
    # VALUES (%s, %s)
    # ON CONFLICT (id) DO UPDATE
    # SET embedding = EXCLUDED.embedding
    # """

    # data = [(r["id"], r["embedding"]) for r in rows]

    # with conn.cursor() as cur:
    #     execute_batch(cur, sql, data, page_size=1000)

    # conn.commit()
    # conn.close()




    # job_df.select("id", "tfidf_features").show()



    
    



    spark.stop()
if __name__ == "__main__":
    main()