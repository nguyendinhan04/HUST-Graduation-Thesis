from kubernetes.stream import stream
from minio import Minio
from dotenv import load_dotenv
import os
from .default_config import DEFAULTS
from io import BytesIO,StringIO

load_dotenv()

class MinioClient:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", DEFAULTS["MINIO_ENDPOINT"])
        self.access_key = os.getenv("MINIO_ACCESS_KEY", DEFAULTS["MINIO_ACCESS_KEY"])
        self.secret_key = os.getenv("MINIO_SECRET_KEY", DEFAULTS["MINIO_SECRET_KEY"])
        self.secure = bool(os.getenv("MINIO_SECURE", DEFAULTS["MINIO_SECURE"]))
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
    def put_object(self, bucket_name: str, object_name: str, input_data):
        encode_data = input_data.encode('utf-8')
        input_stream = BytesIO(encode_data)
        input_stream.seek(0)

        self.client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=input_stream,
            length=len(encode_data)
        )
    def get_text_file(self, bucket_name: str, object_name: str):
                response = self.client.get_object(bucket_name, object_name)
                try:
                    content = response.read().decode('utf-8')
                finally:
                    response.close()
                    response.release_conn()
                return content
    def get_object_name_from_bucket(self, bucket_name: str, prefix: str):
        objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)
        object_names = [obj.object_name for obj in objects]
        return object_names
        