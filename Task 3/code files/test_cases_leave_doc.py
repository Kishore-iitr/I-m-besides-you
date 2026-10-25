import sys, os, json, re
from datetime import datetime
from pathlib import Path

CURRENT_SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_SCRIPT_DIR
while ROOT_DIR.name in ('code files', 'code', 'Task 3', 'task 3', 'Task 2', 'task 2', 'Task 1', 'task 1'):
    ROOT_DIR = ROOT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(CURRENT_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_SCRIPT_DIR))
from erp_db import db_manager

# 15 Test Cases with Realistic Raw OCR Text from Documents in Windows Explorer
TEST_CASES = [
    {
        "id": "LV-TEST-001",
        "employee_id": "EMP-2001",
        "employee_name": "加藤 雅人",
        "department": "営業部",
        "leave_type": "病気休暇",
        "start_date": "2026-07-15",
        "end_date": "2026-07-17",
        "requested_days": 3.0,
        "remaining_balance": 12.0,
        "has_attachment": True,
        "attachment_name": "shindan_sho_kato.pdf",
        "raw_ocr": """医療法人社団 欅会 新宿メディカルクリニック
診断書
患者氏名: 加藤 雅人 殿 (生年月日: 1988年5月12日)
病名: 急性扁桃炎・発熱
上記患者は咽頭痛および高熱を認め、加療を要する。
2026年7月15日より3日間の自宅療養・休業を要すると認める。
発行日: 2026年7月15日
医師氏名: 院長 佐藤 健一 [職印・認印 済]""",
        "expected_doc_features": {
            "patient_name": "加藤 雅人",
            "issue_date": "2026-07-15",
            "recommended_days": 3.0,
            "has_doctor_seal": True,
            "diagnosis": "急性扁桃炎・発熱"
        },
        "expected_status": "Approved",
        "expected_reason": None
    },
    {
        "id": "LV-TEST-002",
        "employee_id": "EMP-2002",
        "employee_name": "高橋 健太",
        "department": "カスタマーサクセス",
        "leave_type": "病気休暇",
        "start_date": "2026-07-20",
        "end_date": "2026-07-23",
        "requested_days": 4.0,
        "remaining_balance": 10.0,
        "has_attachment": True,
        "attachment_name": "shindan_takahashi.pdf",
        "raw_ocr": """品川セントラルクリニック 診断書
氏名: 高橋 健太
病名: 頚椎捻挫
上記につき、2日間の安静加療を要する見込みである。
期間: 2026年7月20日〜2026年7月21日 (2日間)
発行日: 2026年7月20日
担当医: 田中 宏 [認印]""",
        "expected_doc_features": {
            "patient_name": "高橋 健太",
            "issue_date": "2026-07-20",
            "recommended_days": 2.0,
            "has_doctor_seal": True,
            "diagnosis": "頚椎捻挫"
        },
        "expected_status": "Hold",
        "expected_reason": "休職指示日数不足 (申請4日に対し診断書2日)"
    },
    {
        "id": "LV-TEST-003",
        "employee_id": "EMP-2003",
        "employee_name": "山口 翔太",
        "department": "財務経理部",
        "leave_type": "病気休暇",
        "start_date": "2026-07-22",
        "end_date": "2026-07-24",
        "requested_days": 3.0,
        "remaining_balance": 8.0,
        "has_attachment": True,
        "attachment_name": "med_cert_yamaguchi.pdf",
        "raw_ocr": """赤坂胃腸科内科 診断書
患者氏名: 山口 美咲 殿
病名: 感染性胃腸炎
上記患者は脱水症状のため、2026年7月22日より3日間の安静を要する。
発行日: 2026年7月22日
医療機関: 赤坂胃腸科内科 院長 赤坂 太郎 [院長印]""",
        "expected_doc_features": {
            "patient_name": "山口 美咲",
            "issue_date": "2026-07-22",
            "recommended_days": 3.0,
            "has_doctor_seal": True,
            "diagnosis": "感染性胃腸炎"
        },
        "expected_status": "Hold",
        "expected_reason": "名義不一致 (申請者:山口翔太 vs 診断書:山口美咲)"
    },
    {
        "id": "LV-TEST-004",
        "employee_id": "EMP-2004",
        "employee_name": "伊藤 直樹",
        "department": "法務部",
        "leave_type": "病気休暇",
        "start_date": "2026-07-10",
        "end_date": "2026-07-11",
        "requested_days": 2.0,
        "remaining_balance": 14.0,
        "has_attachment": True,
        "attachment_name": "memo_clinic.pdf",
        "raw_ocr": """診断メモ (未押印コピー)
患者名: 伊藤 直樹
感冒症状のため2日間休養を要す。
2026/07/10
※ 本紙は正式な診断書ではなく下書きメモです（印鑑なし）""",
        "expected_doc_features": {
            "patient_name": "伊藤 直樹",
            "issue_date": "2026-07-10",
            "recommended_days": 2.0,
            "has_doctor_seal": False,
            "diagnosis": "感冒症状"
        },
        "expected_status": "Hold",
        "expected_reason": "医師認印・職印欠落 (非公式書類)"
    },
    {
        "id": "LV-TEST-005",
        "employee_id": "EMP-2005",
        "employee_name": "渡辺 剛",
        "department": "営業部",
        "leave_type": "病気休暇",
        "start_date": "2026-07-25",
        "end_date": "2026-07-27",
        "requested_days": 3.0,
        "remaining_balance": 9.0,
        "has_attachment": True,
        "attachment_name": "shindan_sho_old.pdf",
        "raw_ocr": """渋谷整形外科 診断書
患者: 渡辺 剛
腰椎症性神経根症
2026年5月10日より3日間の安静療養を要する。
発行日: 2026年5月10日
医師: 渋谷 誠一 [印]""",
        "expected_doc_features": {
            "patient_name": "渡辺 剛",
            "issue_date": "2026-05-10",
            "recommended_days": 3.0,
            "has_doctor_seal": True,
            "diagnosis": "腰椎症性神経根症"
        },
        "expected_status": "Hold",
        "expected_reason": "診断書有効期限超過 (発行から2ヶ月以上経過)"
    },
    {
        "id": "LV-TEST-006",
        "employee_id": "EMP-2006",
        "employee_name": "中村 陽子",
        "department": "人事総務部",
        "leave_type": "有給休暇",
        "start_date": "2026-07-16",
        "end_date": "2026-07-17",
        "requested_days": 2.0,
        "remaining_balance": 15.0,
        "has_attachment": False,
        "attachment_name": None,
        "raw_ocr": None,
        "expected_doc_features": None,
        "expected_status": "Approved",
        "expected_reason": None
    },
    {
        "id": "LV-TEST-007",
        "employee_id": "EMP-2007",
        "employee_name": "小林 亮",
        "department": "マーケティング部",
        "leave_type": "有給休暇",
        "start_date": "2026-07-20",
        "end_date": "2026-07-24",
        "requested_days": 5.0,
        "remaining_balance": 2.0,
        "has_attachment": False,
        "attachment_name": None,
        "raw_ocr": None,
        "expected_doc_features": None,
        "expected_status": "Hold",
        "expected_reason": "有給残日数超過 (申請5日 vs 残2日)"
    },
    {
        "id": "LV-TEST-008",
        "employee_id": "EMP-2008",
        "employee_name": "吉田 浩二",
        "department": "情報システム部",
        "leave_type": "夏季特別休暇",
        "start_date": "2026-08-10",
        "end_date": "2026-08-17",
        "requested_days": 6.0,
        "remaining_balance": 10.0,
        "has_attachment": False,
        "attachment_name": None,
        "raw_ocr": None,
        "expected_doc_features": None,
        "expected_status": "Hold",
        "expected_reason": "連続休暇上限超過 (夏季上限5日超・部門長未決裁)"
    },
    {
        "id": "LV-TEST-009",
        "employee_id": "EMP-2009",
        "employee_name": "斎藤 健",
        "department": "開発本部",
        "leave_type": "慶弔特別休暇",
        "start_date": "2026-07-13",
        "end_date": "2026-07-15",
        "requested_days": 3.0,
        "remaining_balance": 11.0,
        "has_attachment": True,
        "attachment_name": "kaiseki_reijo.pdf",
        "raw_ocr": """会葬礼状
喪主 斎藤 健
故 父 斎藤 一郎 儀 葬儀告別式
日時: 2026年7月14日
場所: 横浜市営斎場
御会葬御礼申し上げます。横浜葬祭センター""",
        "expected_doc_features": {
            "patient_name": "斎藤 健",
            "issue_date": "2026-07-14",
            "recommended_days": 3.0,
            "has_doctor_seal": True,
            "diagnosis": "忌引・実父逝去"
        },
        "expected_status": "Approved",
        "expected_reason": None
    },
    {
        "id": "LV-TEST-010",
        "employee_id": "EMP-2010",
        "employee_name": "松本 大輔",
        "department": "営業部",
        "leave_type": "慶弔特別休暇",
        "start_date": "2026-07-28",
        "end_date": "2026-07-30",
        "requested_days": 3.0,
        "remaining_balance": 10.0,
        "has_attachment": False,
        "attachment_name": None,
        "raw_ocr": None,
        "expected_doc_features": None,
        "expected_status": "Hold",
        "expected_reason": "証明書類未添付 (慶弔特別休暇要証明)"
    },
    {
        "id": "LV-TEST-011",
        "employee_id": "EMP-2011",
        "employee_name": "井上 真一",
        "department": "財務経理部",
        "leave_type": "育児休業",
        "start_date": "2026-08-01",
        "end_date": "2026-08-14",
        "requested_days": 10.0,
        "remaining_balance": 20.0,
        "has_attachment": True,
        "attachment_name": "shusshou_todoke.pdf",
        "raw_ocr": """出生届出済証明書
子の氏名: 井上 結菜
父の氏名: 井上 真一
母の氏名: 井上 綾子
出生年月日: 2026年7月20日
上記届出を受理したことを証明する。
2026年7月21日 東京都世田谷区長 [公印]""",
        "expected_doc_features": {
            "patient_name": "井上 真一",
            "issue_date": "2026-07-21",
            "recommended_days": 10.0,
            "has_doctor_seal": True,
            "diagnosis": "育児休業・出生届確認済"
        },
        "expected_status": "Approved",
        "expected_reason": None
    },
    {
        "id": "LV-TEST-012",
        "employee_id": "EMP-2012",
        "employee_name": "木村 拓也",
        "department": "カスタマーサクセス",
        "leave_type": "病気休暇",
        "start_date": "2026-07-21",
        "end_date": "2026-07-27",
        "requested_days": 5.0,
        "remaining_balance": 15.0,
        "has_attachment": False,
        "attachment_name": None,
        "raw_ocr": None,
        "expected_doc_features": None,
        "expected_status": "Hold",
        "expected_reason": "医師診断書未提出 (3日超病気休暇要診断書)"
    },
    {
        "id": "LV-TEST-013",
        "employee_id": "EMP-2013",
        "employee_name": "清水 美紀",
        "department": "人事総務部",
        "leave_type": "半日有給申請",
        "start_date": "2026-07-17",
        "end_date": "2026-07-17",
        "requested_days": 0.5,
        "remaining_balance": 8.5,
        "has_attachment": False,
        "attachment_name": None,
        "raw_ocr": None,
        "expected_doc_features": None,
        "expected_status": "Approved",
        "expected_reason": None
    },
    {
        "id": "LV-TEST-014",
        "employee_id": "EMP-2014",
        "employee_name": "林 太郎",
        "department": "開発本部",
        "leave_type": "有給休暇",
        "start_date": "2026-07-30",
        "end_date": "2026-07-31",
        "requested_days": 2.0,
        "remaining_balance": 10.0,
        "has_attachment": False,
        "attachment_name": None,
        "raw_ocr": None,
        "expected_doc_features": None,
        "expected_status": "Hold",
        "expected_reason": "開発部リリース凍結期間申請制限"
    },
    {
        "id": "LV-TEST-015",
        "employee_id": "EMP-2015",
        "employee_name": "阿部 浩",
        "department": "法務部",
        "leave_type": "病気休暇",
        "start_date": "2026-07-14",
        "end_date": "2026-07-27",
        "requested_days": 10.0,
        "remaining_balance": 18.0,
        "has_attachment": True,
        "attachment_name": "hospital_inpatient_cert.pdf",
        "raw_ocr": """東京大学医学部附属病院 入院証明・診断書
患者氏名: 阿部 浩
生年月日: 1980年3月4日
病名: 急性虫垂炎 (腹腔鏡下切除術施行)
上記疾患により入院手術加療を実施した。
入院および自宅安静期間として、2026年7月14日より10日間の就労不能と認める。
発行日: 2026年7月14日
病院長・主治医: 教授 山本 晋 [病院公印・職印あり]""",
        "expected_doc_features": {
            "patient_name": "阿部 浩",
            "issue_date": "2026-07-14",
            "recommended_days": 10.0,
            "has_doctor_seal": True,
            "diagnosis": "急性虫垂炎・術後休業"
        },
        "expected_status": "Approved",
        "expected_reason": None
    }
]

print(f"Loaded {len(TEST_CASES)} test cases for Document Intelligence & Rule Pipeline.")
