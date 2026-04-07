import pandas as pd
import glob

# 합칠 파일 목록
files = [
    'C:\\Users\\smhrd\\Desktop\\backend\\data\\corrections_500.xlsx',
    'C:\\Users\\smhrd\\Desktop\\backend\\data\\merged_data_clean_4.xlsx'
]

# 파일 합치기
dfs = []
for file in files:
    df = pd.read_excel(file)
    print(f"{file} → {len(df)}개")
    dfs.append(df)

# 합치기
merged = pd.concat(dfs, ignore_index=True)

# 중복 제거
merged = merged.drop_duplicates(subset=['original_text'])

print(f"\n총 합계: {len(merged)}개")
print(f"맥락별 데이터 수:\n{merged['context_type'].value_counts()}")

# 저장
merged.to_excel(
    'C:\\Users\\smhrd\\Desktop\\backend\\merged_data.xlsx',
    index=False
)
print("\n저장 완료! (merged_data.xlsx)")