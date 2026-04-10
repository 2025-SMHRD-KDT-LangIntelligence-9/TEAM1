import pandas as pd
from database import SessionLocal
from models import Embeddings
from kobert_transformers import get_tokenizer
from transformers import BertModel
import torch
from tqdm import tqdm

# KoBERT 모델 로드
print("KoBERT 모델 로딩 중...")
tokenizer = get_tokenizer()
model = BertModel.from_pretrained('monologg/kobert')
model.eval()

def get_vector(text: str) -> list:
    """텍스트를 KoBERT로 벡터화 (768차원)"""
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

# 데이터 로드
print("데이터 로딩 중...")
df = pd.read_excel(r'C:\Users\smhrd\Desktop\backend\data\데이터파일.xlsx')
print(f"총 데이터 수: {len(df)}개")
print(f"맥락별 데이터:\n{df['context_type'].value_counts()}\n")

# DB 세션
db = SessionLocal()

try:
    # 기존 데이터 삭제 (재삽입 시 중복 방지)
    existing = db.query(Embeddings).count()
    if existing > 0:
        print(f"기존 데이터 {existing}개 삭제 중...")
        db.query(Embeddings).delete()
        db.commit()
        print("기존 데이터 삭제 완료!")

    # 데이터 삽입
    print("벡터화 및 DB 삽입 중...")
    for _, row in tqdm(df.iterrows(), total=len(df), desc="삽입 진행", unit="개"):
        # original_text 벡터화
        vector = get_vector(str(row['original_text']))

        embedding = Embeddings(
            original_text=str(row['original_text']),
            corrected_text=vector,
            corrected_text_raw=str(row['corr_text']),
            context_type=str(row['context_type'])
        )
        db.add(embedding)

    db.commit()
    print(f"\nDB 삽입 완료! 총 {len(df)}개")

except Exception as e:
    db.rollback()
    print(f"에러 발생: {e}")
finally:
    db.close()
