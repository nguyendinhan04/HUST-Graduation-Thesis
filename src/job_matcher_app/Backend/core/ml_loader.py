import pickle
import boto3
import logging
from sentence_transformers import SentenceTransformer
from config import get_settings
import numpy as np

class TFIDFModel:
    def __init__(self, svd, vectorizer, n_components):
        self.svd = svd
        self.vectorizer = vectorizer
        self.n_components = n_components

    def get_query_vector(self, query: str):
        query_vec = self.vectorizer.transform([query])
        query_vec_svd = self.svd.transform(query_vec)
        return query_vec_svd
    

class BERTModel:
    def __init__(self, model):
        self.model = model

    def get_query_vector(self, query: str):
        # Giả sử model đã được fine-tune để trả về vector embedding
        query_vec = self.model.encode([query])
        return query_vec


    def get_document_embedding(self,text ,max_words_per_chunk=300):
        words = text.split()
        # Chia text thành các đoạn nhỏ (chunk)
        chunks = [" ".join(words[i:i + max_words_per_chunk]) for i in range(0, len(words), max_words_per_chunk)]
        
        if not chunks:
            chunks = [""] # Xử lý trường hợp text rỗng
            
        # Lấy embedding cho từng chunk (model.encode trả về vector của [CLS] hoặc output tương đương của cấu trúc Transformer)
        chunk_embeddings = self.model.encode(chunks)
        
        # Tính trung bình (Mean Pooling) các chunks để ra vector đại diện cho toàn bộ văn bản
        doc_embedding = np.mean(chunk_embeddings, axis=0)
        
        # Chuẩn hóa độ dài của vector (L2 normalization) 
        # Giúp việc tính Cosine Distance sau này chính xác hơn
        doc_embedding = doc_embedding / np.linalg.norm(doc_embedding)
        
        return doc_embedding

class SkillEmbeddingModel:
    def __init__(self, model):
        self.model = model
    
    def get_skill_embedding(self, skill_name: str):
        skill_vec = self.model.encode([skill_name])
        return skill_vec






class MLModelLoader:
    def __init__(self, config):
        self.config = config
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if self.config.minio_secure else ''}://{self.config.minio_endpoint}",
            aws_access_key_id=self.config.minio_access_key,
            aws_secret_access_key=self.config.minio_secret_key,
            region_name="us-east-1",
        )
    

    @staticmethod
    def load_tfidf_artifacts_from_minio(s3_client, bucket_name, model_key=None, prefix="models/tfidf/"):
        # Nếu chưa truyền key cụ thể thì tự lấy file mới nhất trong prefix
        if model_key is None:
            resp = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            objects = resp.get("Contents", [])
            if not objects:
                raise FileNotFoundError(f"Không tìm thấy model nào trong s3://{bucket_name}/{prefix}")
            latest_obj = max(objects, key=lambda x: x["LastModified"])
            model_key = latest_obj["Key"]

        obj = s3_client.get_object(Bucket=bucket_name, Key=model_key)
        artifacts = pickle.loads(obj["Body"].read())

        logging.info(f"Đã tải model TF-IDF từ MinIO: s3://{bucket_name}/{model_key} (LastModified: {obj['LastModified']})")
        return artifacts, model_key

    def load_model_tfidf(self) -> TFIDFModel:
        tfidf_artifacts_loaded, loaded_key = self.load_tfidf_artifacts_from_minio(
            s3_client=self.s3_client,
            bucket_name=self.config.minio_bucket,
        )

        vectorizer = tfidf_artifacts_loaded["vectorizer"]
        svd = tfidf_artifacts_loaded["svd"]
        n_components = tfidf_artifacts_loaded["n_components"]

        return TFIDFModel(svd=svd, vectorizer=vectorizer, n_components=n_components)

    @staticmethod
    def load_model_BERT_from_HF():
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return BERTModel(model=model)

    @staticmethod
    def load_model_skill_embedding_from_HF():
        model = SentenceTransformer("alvperez/skill-sim-model")
        return SkillEmbeddingModel(model=model)

def create_model_loader() -> MLModelLoader:
    settings = get_settings()
    return MLModelLoader(settings)