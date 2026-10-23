with open('unified_copilot_erp_app.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = 'app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)'
replacement = '''try:
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        import traceback
        traceback.print_exc()'''

if target in c:
    c = c.replace(target, replacement)
    with open('unified_copilot_erp_app.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Updated successfully')
else:
    print('Target not found')
