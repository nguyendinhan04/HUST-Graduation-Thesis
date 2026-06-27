import pickle
import boto3
import logging
from sentence_transformers import SentenceTransformer
from config import get_settings
import numpy as np


    

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