import zipfile
from pathlib import Path

out_dir = Path("sample_word_docs")
out_dir.mkdir(exist_ok=True)
docx_path = out_dir / "it_gyomu_butsuryu_shinsa.docx"

content = """IT業務委託及び物流費臨時精算審査規程 (2026年度版)

【目的】
本規程は、ITシステム開発委託費および物流関連調整費の請求書承認における審査基準および承認権限を定める。

【第1条: ITシステム開発委託費の承認規則】
1. 対象取引先: 福岡システム設計
2. 請求金額が月次契約予算枠（金2,000,000円）未満である場合、検収確認完了として承認する。
   入力コメント: 「IT業務委託契約・検収完了及び月次予算枠内確認済」
3. 請求金額が2,000,000円以上の場合は、追加工数稟議が必要となるため保留とする。
   入力コメント: 「IT開発予算上限超過・要確認保留」

【第2条: 物流関連調整費の承認規則】
1. 対象取引先: 沖縄物流センター
2. 処理区分が「調整」であり、請求金額が金500,000円未満の場合は、実績明細照合完了として承認する。
   入力コメント: 「物流倉庫調整費・実績明細突合完了・承認」
3. 500,000円以上の場合は部門長決裁が必要なため保留とする。
   入力コメント: 「物流調整費50万円超・部門長確認保留」

【第3条: 製造部品調整費の審査規則】
1. 対象取引先: 北陸部品工業株式会社
2. 処理区分が「調整」の請求書は、品質検査報告書の受領照合が完了するまで即時承認を行わず保留とする。
   入力コメント: 「製造調整費・受入品質検査報告書未確認保留」

【第4条: その他取引先の扱い】
1. 本規程の対象外である定常月次仕入・製造費（山田製作所、大和商事等）は通常定額審査部門へ回送し保留とする。
   入力コメント: 「特定業務委託規程対象外・通常審査へ回送保留」
"""

def make_docx(text, out_file):
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '  <Default Extension="xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
        '</Relationships>'
    )
    body_paragraphs = []
    for line in text.splitlines():
        line_escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        body_paragraphs.append(f'<w:p><w:r><w:t>{line_escaped}</w:t></w:r></w:p>')
    body_xml = ''.join(body_paragraphs)

    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        f'  <w:body>{body_xml}</w:body>\n'
        '</w:document>'
    )

    with zipfile.ZipFile(out_file, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', rels)
        z.writestr('word/document.xml', doc_xml)

make_docx(content, docx_path)
print("Successfully generated:", docx_path.resolve())
