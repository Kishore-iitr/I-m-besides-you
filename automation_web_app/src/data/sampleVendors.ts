import { VendorContract } from '../types';

export const INITIAL_VENDOR_CONTRACTS: VendorContract[] = [
  {
    id: 'vc-001',
    vendor_code: 'V3001',
    vendor_name: '株式会社山田製作所',
    base_amount: 340285,
    tax_rate: 0.10,
    tax_amount: 34028,
    total_amount: 374313,
    service_scope: '精密機械部品定期保守・金型メンテナンス支援',
    payment_terms: '月末締め翌月末銀行振込',
    document_source: 'getsujitsu_teigaku_torihikisaki_ichiran.docx',
    status: 'ACTIVE'
  },
  {
    id: 'vc-002',
    vendor_code: 'V3002',
    vendor_name: '大和商事株式会社',
    base_amount: 1124945,
    tax_rate: 0.10,
    tax_amount: 112494,
    total_amount: 1237439,
    service_scope: 'オフィスサプライ・包装資材定額納入契約',
    payment_terms: '月末締め翌月末振込',
    document_source: 'getsujitsu_teigaku_torihikisaki_ichiran.docx',
    status: 'ACTIVE'
  },
  {
    id: 'vc-003',
    vendor_code: 'V3003',
    vendor_name: '東京電子工業株式会社',
    base_amount: 478182,
    tax_rate: 0.10,
    tax_amount: 47818,
    total_amount: 526000,
    service_scope: '基板定期検査・ファームウェアアップデート保守',
    payment_terms: '月末締め翌月末手形',
    document_source: 'getsujitsu_teigaku_torihikisaki_ichiran.docx',
    status: 'ACTIVE'
  },
  {
    id: 'vc-004',
    vendor_code: 'V3004',
    vendor_name: '関西物流サービス',
    base_amount: 2948300,
    tax_rate: 0.10,
    tax_amount: 294830,
    total_amount: 3243130,
    service_scope: '西日本主要拠点定期幹線輸送 (定額定期便)',
    payment_terms: '毎月末締め翌月25日振込',
    document_source: 'getsujitsu_teigaku_torihikisaki_ichiran.docx',
    status: 'ACTIVE'
  },
  {
    id: 'vc-005',
    vendor_code: 'V3005',
    vendor_name: 'グローバルテック合同会社',
    base_amount: 651120,
    tax_rate: 0.10,
    tax_amount: 65112,
    total_amount: 716232,
    service_scope: '基幹ERPクラウドサーバー保守・24時間365日監視',
    payment_terms: '月末締め翌月20日振込',
    document_source: 'getsujitsu_teigaku_torihikisaki_ichiran.docx',
    status: 'ACTIVE'
  },
  {
    id: 'vc-006',
    vendor_code: 'V3006',
    vendor_name: '北陸部品工業株式会社',
    base_amount: 413753,
    tax_rate: 0.10,
    tax_amount: 41375,
    total_amount: 455128,
    service_scope: '成型プラスチック樹脂部品定額供給',
    payment_terms: '月末締め翌月末振込',
    document_source: 'getsujitsu_teigaku_torihikisaki_ichiran.docx',
    status: 'ACTIVE'
  },
  {
    id: 'vc-007',
    vendor_code: 'V3007',
    vendor_name: '福岡システム設計',
    base_amount: 1532168,
    tax_rate: 0.10,
    tax_amount: 153216,
    total_amount: 1685384,
    service_scope: '受発注EDI連携モジュール保守運用サポート常駐',
    payment_terms: '当月末締め翌月末振込',
    document_source: 'getsujitsu_teigaku_torihikisaki_ichiran.docx',
    status: 'ACTIVE'
  },
  {
    id: 'vc-008',
    vendor_code: 'V3008',
    vendor_name: '沖縄物流センター',
    base_amount: 273839,
    tax_rate: 0.10,
    tax_amount: 27384,
    total_amount: 301223,
    service_scope: '南西諸島定期海上コンテナ中継ハブ利用料',
    payment_terms: '月末締め翌月10日振込',
    document_source: 'getsujitsu_teigaku_torihikisaki_ichiran.docx',
    status: 'ACTIVE'
  }
];
