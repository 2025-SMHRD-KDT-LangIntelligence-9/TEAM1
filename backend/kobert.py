from kobert_transformers import get_tokenizer
from transformers import BertModel
import torch

# KoBERT 모델 로드
tokenizer = get_tokenizer()
model = BertModel.from_pretrained('monologg/kobert')

def analyze_emotion(text: str) -> dict:
    # 텍스트 토큰화
    inputs = tokenizer(
        text,
        return_tensors='pt',
        max_length=128,
        truncation=True,
        padding=True
    )
    
    with torch.no_grad():
        outputs = model(**inputs)
    
    # 문장 전체 벡터 추출
    pooled_output = outputs.pooler_output
    
    # 벡터 평균값으로 감정 강도 계산 (임시)
    emotion_score = pooled_output.mean().item()
    
    # 감정 레이블 판단 (임시 기준)
    if emotion_score < -0.1:
        emotion_label = "부정"
    elif emotion_score > 0.1:
        emotion_label = "긍정"
    else:
        emotion_label = "중립"
    
    return {
        "text": text,
        "emotion_label": emotion_label,
        "emotion_score": round(emotion_score, 4)
    }

# 테스트
if __name__ == "__main__":
    texts = [
        "이거 왜 아직도 안 됐어요?",
        "진행 상황 공유해 주실 수 있을까요?",
        "빨리 좀 처리해주세요",
        "안녕하세요 잘 부탁드립니다"
    ]
    
    for text in texts:
        result = analyze_emotion(text)
        print(f"텍스트: {result['text']}")
        print(f"감정: {result['emotion_label']} ({result['emotion_score']})")
        print()