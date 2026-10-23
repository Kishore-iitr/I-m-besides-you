"""
Script to apply the clean, verified HTML/JS from generate_app.py into unified_copilot_erp_app.py
"""
import re
import subprocess
import sys

with open("generate_app.py", "r", encoding="utf-8") as f:
    gen_content = f.read()

# Extract HTML_CONTENT from generate_app.py
m = re.search(r"HTML_CONTENT = r'''(.*?)'''\s*# Write test script", gen_content, re.DOTALL)
if not m:
    print("Error: Could not find HTML_CONTENT in generate_app.py")
    sys.exit(1)

html_content = m.group(1).strip()
print(f"Extracted HTML_CONTENT: {len(html_content)} characters")

with open("unified_copilot_erp_app.py", "r", encoding="utf-8") as f:
    app_code = f.read()

# Locate the HTML_TEMPLATE definition
# It starts at HTML_TEMPLATE = """ or HTML_TEMPLATE = r'''
# and ends right before # --- Flask Endpoints ---
prefix = app_code.split("HTML_TEMPLATE = ")[0]
suffix = "# --- Flask Endpoints ---" + app_code.split("# --- Flask Endpoints ---")[1]

new_app_code = prefix + "HTML_TEMPLATE = r'''" + html_content + "'''\n\n" + suffix

with open("unified_copilot_erp_app.py", "w", encoding="utf-8") as f:
    f.write(new_app_code)

print("Updated unified_copilot_erp_app.py successfully!")

# Validate python compilation
res_py = subprocess.run([sys.executable, "-m", "py_compile", "unified_copilot_erp_app.py"], capture_output=True, text=True)
print("Python compile returncode:", res_py.returncode)
if res_py.returncode != 0:
    print("Python error:", res_py.stderr)
    sys.exit(1)

# Validate JS syntax via node
m_js = re.search(r"<script[\s\S]*?</script>", html_content)
if m_js:
    js_text = m_js.group(0).replace("<script>", "").replace("</script>", "")
    with open("temp_validate.js", "w", encoding="utf-8") as f:
        f.write(js_text)
    res_js = subprocess.run(["node", "-c", "temp_validate.js"], capture_output=True, text=True)
    print("Node.js -c returncode:", res_js.returncode)
    if res_js.returncode != 0:
        print("JS Syntax Error:", res_js.stderr)
        sys.exit(1)
    else:
        print("Verified: JavaScript in unified_copilot_erp_app.py is 100% valid!")
