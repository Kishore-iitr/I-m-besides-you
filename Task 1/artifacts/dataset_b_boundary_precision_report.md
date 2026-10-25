# Dataset B Dual-Horizon Visual Boundary Precision & Transition Evaluation Report

**Total Dataset B Segments Evaluated**: 158 (Across 15 Sessions)

## 1. Executive Metric Summary

| Evaluation Horizon | Metric Name | Measured Score | Evaluation Meaning |
| :--- | :--- | :---: | :--- |
| **Inside Segment** | Internal Visual Alignment | **89.87%** | Screenshots/events during task match predicted label. |
| **Before Boundary** | Terminal Pre-Boundary Match | **91.77%** | Screenshot immediately before `end` shows task being finished. |
| **After Boundary** | Exterior Post-Boundary Transition | **93.04%** | Screenshot 1–6s after `end` transitions away from the old task. |
| **Dual-Horizon** | **Dual-Horizon Boundary Precision** | **85.44%** | **Strict joint pass: Before matches AND After transitions.** |

## 2. Per-Session Precision Breakdown

| Session ID | Segments | Pre-End Match | Post-End Transition | Dual-Horizon Precision |
| :--- | :---: | :---: | :---: | :---: |
| `ses_20260701-164424-CHAITANYA0BCF` | 14 | 14/14 | 13/14 | **92.9%** |
| `ses_20260701-171614-CHAITANYA0BCF` | 12 | 11/12 | 11/12 | **83.3%** |
| `ses_20260701-173246-SIDDHIGUPTAB00B` | 11 | 10/11 | 11/11 | **90.9%** |
| `ses_20260701-173642-NEELA9BAF` | 13 | 11/13 | 10/13 | **61.5%** |
| `ses_20260701-175258-LAPTOP-76QMG9DE` | 13 | 13/13 | 13/13 | **100.0%** |
| `ses_20260701-175747-SIDDHIGUPTAB00B` | 11 | 10/11 | 10/11 | **81.8%** |
| `ses_20260701-180923-NEELA9BAF` | 8 | 7/8 | 8/8 | **87.5%** |
| `ses_20260701-181413-LAPTOP-76QMG9DE` | 16 | 14/16 | 16/16 | **87.5%** |
| `ses_20260701-181913-SIDDHIGUPTAB00B` | 9 | 9/9 | 8/9 | **88.9%** |
| `ses_20260701-182634-NEELA9BAF` | 10 | 8/10 | 10/10 | **80.0%** |
| `ses_20260701-183232-LAPTOP-76QMG9DE` | 5 | 5/5 | 3/5 | **60.0%** |
| `ses_20260701-184201-LAPTOP-76QMG9DE` | 12 | 10/12 | 12/12 | **83.3%** |
| `ses_20260701-190250-NEELA9BAF` | 14 | 14/14 | 13/14 | **92.9%** |
| `ses_20260701-191537-LAPTOP-76QMG9DE` | 7 | 6/7 | 6/7 | **85.7%** |
| `ses_20260701-192455-NEELA9BAF` | 3 | 3/3 | 3/3 | **100.0%** |
