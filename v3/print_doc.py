import docx

doc = docx.Document('sample_word_docs/it_gyomu_butsuryu_shinsa.docx')
with open('doc2_text.txt', 'w', encoding='utf-8') as out:
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip():
            out.write(f"{i}: {p.text}\n")

print("Saved to doc2_text.txt")
