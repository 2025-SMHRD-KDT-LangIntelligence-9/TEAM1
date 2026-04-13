import numpy as np
import pickle
import os
from kobert_transformers import get_tokenizer
from transformers import BertModel
from database import SessionLocal
from models import Embeddings, Correction
import torch

# KoBERT 모델 로드
tokenizer = get_tokenizer()
model = BertModel.from_pretrained('monologg/kobert')
model.eval()

# 맥락 분류기 로드 (현재 파일 기준 상대경로)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, 'context_classifier.pkl'), 'rb') as f:
    saved = pickle.load(f)
    classifier = saved['classifier']
    label_encoder = saved['label_encoder']

def get_vector(text: str) -> list:
    inputs = tokenizer(
        text,
        return_tensors='pt',
        max_length=128,
        truncation=True,
        padding=True
    )
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.pooler_output.squeeze().tolist()

def predict_context(text: str) -> tuple:
    """맥락 예측 + 확률 반환"""
    vector = np.array(get_vector(text)).reshape(1, -1)
    pred = classifier.predict(vector)
    proba = classifier.predict_proba(vector)[0]
    max_proba = max(proba)
    context_type = label_encoder.inverse_transform(pred)[0]
    return context_type, max_proba

def search_similar(text: str, limit: int = 3):
    # 1. 벡터화
    vector = get_vector(text)

    # 2. 맥락 예측 + 확률 확인
    context_type, confidence = predict_context(text)

    db = SessionLocal()
    try:
        if confidence >= 0.6:
            # 확률 높으면 → 해당 맥락으로 필터링 검색
            print(f"맥락 확정: {context_type} (확률: {confidence:.2f})")
            results = db.query(Embeddings).filter(
                Embeddings.context_type == context_type
            ).order_by(
                Embeddings.corrected_text.l2_distance(vector)
            ).limit(limit).all()
        else:
            # 확률 낮으면 → 맥락 불명확 → 전체에서 검색
            print(f"맥락 불명확: {context_type} (확률: {confidence:.2f}) → LLM이 판단")
            context_type = "불명확"
            results = db.query(Embeddings).order_by(
                Embeddings.corrected_text.l2_distance(vector)
            ).limit(limit).all()

        similar_texts = [
            {
                "original_text": r.original_text,
                "corr_text": r.corrected_text_raw,
                "context_type": r.context_type
            }
            for r in results
        ]

        return similar_texts, context_type

    finally:
        db.close()

def search_history(text: str, user_id: int, limit: int = 3):
    """사용자의 이전 교정 히스토리에서 유사한 텍스트 검색"""
    vector = get_vector(text)

    db = SessionLocal()
    try:
        results = db.query(Correction).filter(
            Correction.id == user_id,
            Correction.upload_vector != None
        ).order_by(
            Correction.upload_vector.l2_distance(vector)
        ).limit(limit).all()

        return [
            {
                "original_text": r.upload_text,
                "corr_text": r.corr_text,
                "context_type": r.tone_type
            }
            for r in results
        ]
    finally:
        db.close()