with open("copilot_langgraph_engine.py", "r", encoding="utf-8") as f:
    text = f.read()

target = '            # --- Rule Case C: Unregistered Vendor Check ---'
replacement = '''            if "未登録" in line:
                print("DEBUG: Line reached before Case C, line is:", line)
            # --- Rule Case C: Unregistered Vendor Check ---'''

text = text.replace(target, replacement)
with open("copilot_langgraph_engine.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Added debug print to copilot_langgraph_engine.py")
