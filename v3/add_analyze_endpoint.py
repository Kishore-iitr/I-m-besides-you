with open("unified_copilot_erp_app.py", "r", encoding="utf-8") as f:
    code = f.read()

target = """@app.route("/api/copilot/evaluate", methods=["POST"])
def evaluate_copilot():
    data = request.json or {}
    process_type = data.get("process_type", "invoice")
    doc_text = data.get("document_text", "")
    filename = data.get("filename_or_title", "Policy Document")

    result = copilot_engine.evaluate(
        process_type=process_type,
        document_text=doc_text,
        filename_or_title=filename
    )
    return jsonify(result)"""

replacement = """@app.route("/api/copilot/analyze", methods=["POST"])
def analyze_copilot():
    data = request.json or {}
    process_type = data.get("process_type", "invoice")
    doc_text = data.get("document_text", "")
    filename = data.get("filename_or_title", "Policy Document")

    result = copilot_engine.analyze_policy(
        process_type=process_type,
        document_text=doc_text,
        filename_or_title=filename
    )
    return jsonify(result)

@app.route("/api/copilot/evaluate", methods=["POST"])
def evaluate_copilot():
    data = request.json or {}
    process_type = data.get("process_type", "invoice")
    doc_text = data.get("document_text", "")
    filename = data.get("filename_or_title", "Policy Document")
    custom_rules = data.get("custom_rules")

    result = copilot_engine.evaluate(
        process_type=process_type,
        document_text=doc_text,
        filename_or_title=filename,
        custom_rules=custom_rules
    )
    return jsonify(result)"""

norm_code = code.replace("\r\n", "\n")
norm_target = target.replace("\r\n", "\n")
norm_rep = replacement.replace("\r\n", "\n")

if norm_target in norm_code:
    norm_code = norm_code.replace(norm_target, norm_rep, 1)
    with open("unified_copilot_erp_app.py", "w", encoding="utf-8") as f:
        f.write(norm_code)
    print("Successfully added /api/copilot/analyze and updated /api/copilot/evaluate in unified_copilot_erp_app.py!")
else:
    print("Error: Target not found in code")
