import pandas as pd
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
import numpy as np
import pickle
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
df = pd.read_excel(r'C:\Users\smhrd\Desktop\backend\data\데이터파일 (5).xlsx')
print(f"원본 데이터 수: {len(df)}개")

# original_text + corr_text 각각 따로 행으로 만들기
# original_text + corr_text
texts = []
labels = []

for _, row in df.iterrows():
    # original_text 추가
    texts.append(str(row['original_text']))
    labels.append(row['context_type'])
    # corr_text 추가 (같은 맥락 레이블)
    texts.append(str(row['corr_text']))
    labels.append(row['context_type'])

print(f"총 학습 데이터 수: {len(texts)}개 (원본 {len(df)}개 × 2)")

# 벡터화
print("\n텍스트 벡터화 중...")
X = []
for text in tqdm(texts, desc="벡터화 진행", unit="개"):
    vector = get_vector(text)
    X.append(vector)

X = np.array(X)
print(f"벡터 shape: {X.shape}")  # (1956, 768)

# 레이블 인코딩
le = LabelEncoder()

y = le.fit_transform(labels)
print(f"맥락 클래스: {le.classes_}")

# 학습/테스트 분리 (80% 학습 / 20% 테스트)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\n학습 데이터: {len(X_train)}개 / 테스트 데이터: {len(X_test)}개")

# MLP 학습
print("\nMLP 학습 중...")
clf = MLPClassifier(
    hidden_layer_sizes=(512, 256),
    activation='relu',
    max_iter=500,
    random_state=42,
    verbose=True
)
clf.fit(X_train, y_train)
print("MLP 학습 완료!")

# 성능 평가
y_pred = clf.predict(X_test)
print("\n=== 성능 평가 ===")
print(classification_report(y_test, y_pred, target_names=le.classes_))

# 모델 저장
save_path = r'C:\Users\smhrd\Desktop\backend\context_classifier.pkl'
with open(save_path, 'wb') as f:
    pickle.dump({'classifier': clf, 'label_encoder': le}, f)
print(f"모델 저장 완료! ({save_path})")

# 테스트 - 새로운 텍스트 하나만 입력
def predict_context(text: str) -> str:
    vector = np.array(get_vector(text)).reshape(1, -1)
    pred = clf.predict(vector)
    return le.inverse_transform(pred)[0]

print("\n=== 테스트 ===")
test_cases = [
    "이거 왜 아직도 안 됐어요?",
    "보고서 왜 이렇게 늦어?",
    "빨리 좀 해주세요.",
    "그건 말이 안 되잖아요.",
    "이게 제 잘못이에요?",
    "정말 수고 많으셨습니다.",
    "이거 오늘까지 끝내.",
    "왜 이렇게 모르는 게 많아요?",
]

for text in tqdm(test_cases, desc="테스트 진행", unit="개"):
    context = predict_context(text)
    print(f"  '{text}' → {context}")