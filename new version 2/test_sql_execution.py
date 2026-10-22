from erp_db import db_manager
import psycopg2.extras

with db_manager._get_pg_conn() as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        q_approve = "SELECT id, invoice_no, name, raw_amount FROM erp_invoices WHERE (name = 'Yamada Manufacturing Co., Ltd.' AND raw_amount = 385000) OR (name = 'Yamato Shoji Co., Ltd.' AND raw_amount = 1240000) OR (name = 'Global Tech LLC' AND raw_amount = 745000) OR (name = 'Tokyo Electronics Industry Co., Ltd.' AND raw_amount = 562800) OR (name = 'Hokuriku Parts Industry Co., Ltd.' AND raw_amount = 420000);"
        cur.execute(q_approve)
        approved = cur.fetchall()
        print('Approved rows count:', len(approved))
        for r in approved:
            print(' -> Approved:', r['id'], r['invoice_no'], r['name'], r['raw_amount'])
            
        q_hold = "SELECT id, invoice_no, name, raw_amount FROM erp_invoices WHERE (name = 'Yamada Manufacturing Co., Ltd.' AND raw_amount != 385000) OR (name = 'Yamato Shoji Co., Ltd.' AND raw_amount != 1240000) OR (name = 'Global Tech LLC' AND raw_amount != 745000) OR (name = 'Tokyo Electronics Industry Co., Ltd.' AND raw_amount != 562800) OR (name = 'Hokuriku Parts Industry Co., Ltd.' AND raw_amount != 420000) OR (name NOT IN ('Yamada Manufacturing Co., Ltd.', 'Yamato Shoji Co., Ltd.', 'Global Tech LLC', 'Tokyo Electronics Industry Co., Ltd.', 'Hokuriku Parts Industry Co., Ltd.'));"
        cur.execute(q_hold)
        held = cur.fetchall()
        print('Held rows count:', len(held))
        for r in held[:4]:
            print(' -> Held:', r['id'], r['invoice_no'], r['name'], r['raw_amount'])
