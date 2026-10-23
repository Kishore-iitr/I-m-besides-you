from tmi_pipeline import PuterLlmClient
for model in ['gpt-4o-mini', 'claude-3-5-sonnet', 'mistral-large-latest', 'deepseek-chat']:
    try:
        c = PuterLlmClient(model=model)
        r = c.complete('Reply with {"status": "ok"}')
        print(f"Puter model {model} SUCCESS: {r[:60]}")
        break
    except Exception as e:
        print(f"Puter model {model} Error: {e}")
