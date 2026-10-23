with open("copilot_langgraph_engine.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "cats = re.findall" in l:
        print(f"Found at line {i+1}: {l}")
        lines[i] = "                cats = re.findall(r'[\"\\\']([A-Za-z0-9_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+)[\"\\\']', line)\n"
        break

with open("copilot_langgraph_engine.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Updated copilot_langgraph_engine.py line 303!")
