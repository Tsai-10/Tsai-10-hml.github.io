import pandas as pd

# 讀取 Excel
df = pd.read_excel('1.xlsx')

# 轉成 JSON，orient='records' 方便後端讀取
json_data = df.to_json(orient='records', force_ascii=False)

# 存檔
with open('data.json', 'w', encoding='utf-8') as f:
    f.write(json_data)

print("成功轉成 data.json")
