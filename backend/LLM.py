import ollama

def generate_correction(text: str, context: list, context_type: str, history: list = []) -> dict:

    context_str = "\n".join([
        f"- 원본: {c['original_text']} → 교정: {c['corr_text']}"
        for c in context
    ])

    # 히스토리가 있으면 추가
    history_str = ""
    if history:
        history_str = "\n[이전 교정 히스토리 - 사용자 선호 톤 참고용]:\n" + "\n".join([
            f"- 원본: {h['original_text']} → 교정: {h['corr_text']}"
            for h in history
        ])

    if context_type == "불명확":
        context_desc = "맥락이 명확하지 않으니 텍스트를 직접 분석해서 가장 적절하게 교정해주세요."
    else:
        context_desc = f"현재 대화 맥락은 [{context_type}] 상황입니다."

    prompt = f"""
당신은 직장 내 메신저 소통을 개선하는 전문 AI입니다.

{context_desc}

[참고 교정 예시 - 톤 참고용]:
{context_str}
{history_str}

[입력 텍스트]: {text}

[교정 규칙]:
1. 반드시 입력 텍스트의 의미와 내용을 그대로 유지할 것
2. 참고 예시는 톤과 말투만 참고하고 내용은 따라가지 말 것
3. 히스토리가 있으면 사용자의 선호 톤을 반영할 것
4. 입력 텍스트의 말투(반말/존댓말)를 그대로 유지하며 각 톤에 맞게 교정
   - 존댓말 입력 시:
     - 정중하게: 격식체, "~해 주시겠어요?", "~부탁드립니다"
     - 친근하게: 편안하고 가볍게, "~해줄 수 있어요?", "~해주면 좋겠어요"
     - 단호하게: 짧고 명확하게, "~해주세요", "~완료 부탁드립니다"
   - 반말 입력 시:
     - 정중하게: 부드럽고 예의 바르게, "~해줄 수 있어?", "~부탁해"
     - 친근하게: 편안하고 가볍게, "~해줄 수 있어?", "~해주면 좋겠어"
     - 단호하게: 짧고 명확하게, "~해줘", "~끝내줘"
5. 사용자와 대화를 하는 것이 아닌 사용자의 말을 교정해주는 것이니 주의

반드시 아래 형식으로만 답변하세요:
정중하게: [교정된 문장]
친근하게: [교정된 문장]
단호하게: [교정된 문장]
"""

    response = ollama.chat(
        model='exaone3.5:7.8b',
        messages=[{'role': 'user', 'content': prompt}]
    )

    content = response['message']['content']
    lines = content.strip().split('\n')

    result = {}
    for line in lines:
        if '정중하게:' in line:
            result['polite'] = line.replace('정중하게:', '').strip()
        elif '친근하게:' in line:
            result['friendly'] = line.replace('친근하게:', '').strip()
        elif '단호하게:' in line:
            result['firm'] = line.replace('단호하게:', '').strip()

    return result