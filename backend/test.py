from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import pandas as pd

tokenizer = AutoTokenizer.from_pretrained('monologg/kobert', trust_remote_code=True)
model = AutoModelForSequenceClassification.from_pretrained('rkdaldus/ko-sent5-classification')
model.eval()

emotion_labels = {0: 'Angry', 1: 'Fear', 2: 'Happy', 3: 'Tender', 4: 'Sad'}

df = pd.read_excel(r'data/데이터파일 (8).xlsx')
sample = df.sample(100, random_state=42)

for _, row in sample.iterrows():
    text = str(row['original_text'])
    inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.softmax(outputs.logits, dim=1)[0]
    result = {emotion_labels[i]: round(probs[i].item() * 100, 1) for i in range(5)}
    predicted = max(result, key=result.get)
    print(f'[{row["context_type"]}] {text}')
    print(f'  → 예측: {predicted} | {result}')
    print()