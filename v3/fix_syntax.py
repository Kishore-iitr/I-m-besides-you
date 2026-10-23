with open("copilot_langgraph_engine.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    'has_hold = any(kw in line for kw in ["Hold", "保留", "要確認", "超過", "除外", "精査", "不整合", "差戻し", "以外", "未承認"]):',
    'has_hold = any(kw in line for kw in ["Hold", "保留", "要確認", "超過", "除外", "精査", "不整合", "差戻し", "以外", "未承認"])'
)

text = text.replace(
    "amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\]\\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', line)]",
    "amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\\\]\\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', line)]"
)
text = text.replace(
    "amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\]\\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', line)]",
    "amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\\\]\\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', line)]"
)

with open("copilot_langgraph_engine.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed syntax in copilot_langgraph_engine.py!")
