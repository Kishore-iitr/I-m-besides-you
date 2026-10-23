with open('unified_copilot_erp_app.py', 'r', encoding='utf-8') as f:
    code = f.read()

endpoint_code = """
@app.route("/api/load-sample-doc", methods=["POST"])
def load_sample_doc():
    data = request.json or {}
    doc_type = data.get("type", "invoice")
    sample_dir = Path("sample_word_docs")
    if doc_type == "invoice":
        path = sample_dir / "getsujitsu_teigaku_torihikisaki_ichiran.docx"
    else:
        path = sample_dir / "it_gyomu_butsuryu_shinsa.docx"
    
    if path.exists():
        try:
            with open(path, "rb") as f:
                bytes_data = f.read()
            text = extract_text_from_file_bytes(path.name, bytes_data)
            return jsonify({"success": True, "filename": path.name, "text": text})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "File not found"}), 404
"""

if '/api/load-sample-doc' not in code:
    code = code.replace('@app.route("/api/upload-doc", methods=["POST"])', endpoint_code + '\n@app.route("/api/upload-doc", methods=["POST"])')
    with open('unified_copilot_erp_app.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print('Inserted /api/load-sample-doc')
else:
    print('Endpoint already present')
