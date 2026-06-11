"""
生成示例临床数据
=============
创建用于测试的临床数据集，包含常见的数据质量问题用于演示。
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 将项目根目录加入 sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def generate_dm_dataset(n_subjects: int = 30, include_issues: bool = True) -> pd.DataFrame:
    """
    生成受试者人口学数据 (DM Domain)

    Args:
        n_subjects: 受试者数量
        include_issues: 是否包含数据质量问题

    Returns:
        DM 数据集 DataFrame
    """
    np.random.seed(42)

    data = {
        "STUDYID": ["STUDY001"] * n_subjects,
        "DOMAIN": ["DM"] * n_subjects,
        "USUBJID": [f"STUDY001-SITE{np.random.randint(1,4):03d}-{i+1:04d}" for i in range(n_subjects)],
        "SUBJID": [f"{i+1:04d}" for i in range(n_subjects)],
        "SITEID": [f"SITE{np.random.randint(1,4):03d}" for _ in range(n_subjects)],
        "AGE": np.random.randint(18, 76, n_subjects),
        "AGEU": ["YEARS"] * n_subjects,
        "SEX": np.random.choice(["M", "F", "M", "F", "M"], n_subjects),
        "RACE": np.random.choice(
            ["ASIAN", "WHITE", "BLACK OR AFRICAN AMERICAN", "OTHER"],
            n_subjects, p=[0.6, 0.2, 0.1, 0.1]
        ),
        "ETHNIC": np.random.choice(
            ["NOT HISPANIC OR LATINO", "HISPANIC OR LATINO"],
            n_subjects, p=[0.9, 0.1]
        ),
        "ARM": np.random.choice(
            ["PLACEBO", "TREATMENT_10MG", "TREATMENT_20MG"],
            n_subjects, p=[0.3, 0.35, 0.35]
        ),
        "COUNTRY": ["CHN"] * n_subjects,
        "RFSTDTC": [f"2024-{np.random.randint(1,13):02d}-{np.random.randint(1,28):02d}" for _ in range(n_subjects)],
        "RFENDTC": [""] * n_subjects,
        "WEIGHT": np.random.normal(68, 12, n_subjects).round(1),
        "HEIGHT": np.random.normal(168, 10, n_subjects).round(1),
    }

    df = pd.DataFrame(data)

    # 计算 RFENDTC (在 RFSTDTC 后 30-180 天)
    for i in range(len(df)):
        from datetime import datetime, timedelta
        start = datetime.strptime(df.at[i, "RFSTDTC"], "%Y-%m-%d")
        end = start + timedelta(days=np.random.randint(30, 181))
        df.at[i, "RFENDTC"] = end.strftime("%Y-%m-%d")

    # 计算 BMI
    df["BMI"] = (df["WEIGHT"] / ((df["HEIGHT"] / 100) ** 2)).round(1)

    if include_issues:
        # --- 故意引入的数据质量问题 ---

        # 1. 缺失值
        df.loc[0, "AGE"] = np.nan
        df.loc[1, "SEX"] = np.nan
        df.loc[2, "RACE"] = np.nan

        # 2. 日期格式错误
        df.loc[3, "RFSTDTC"] = "2024/01/15"  # 使用了斜杠格式
        df.loc[4, "RFENDTC"] = "15-03-2024"   # 使用了日-月-年格式

        # 3. 异常值
        df.loc[5, "AGE"] = 999   # 年龄异常
        df.loc[6, "WEIGHT"] = 550.0  # 体重异常
        df.loc[7, "HEIGHT"] = 15.0   # 身高异常
        df.loc[8, "BMI"] = 999.9     # BMI 异常

        # 4. 变量名大小写不一致
        # （这里没法直接 rename，保留原始命名）

        # 5. 分类变量取值错误
        df.loc[9, "SEX"] = "Unknown"  # 非标准取值
        df.loc[10, "RACE"] = "Martian"  # 非标准取值

        # 6. 日期逻辑错误（RFSTDTC > RFENDTC）
        df.loc[11, "RFSTDTC"] = "2024-12-01"
        df.loc[11, "RFENDTC"] = "2024-06-01"  # 开始日期晚于结束日期

        # 7. USUBJID 格式错误
        df.loc[12, "USUBJID"] = "invalid-usubjid-格式错误"
        df.loc[13, "USUBJID"] = "STUDY001-SITE01"  # 缺少受试者编号

        # 8. 重复记录
        duplicate_row = df.iloc[14].copy()
        duplicate_row["SUBJID"] = "9999"
        duplicate_row["USUBJID"] = "STUDY001-SITE01-9999"
        df = pd.concat([df, pd.DataFrame([duplicate_row])], ignore_index=True)

        # 9. 年龄值为负数
        df.loc[15, "AGE"] = -5

    return df


def generate_ae_dataset(n_subjects: int = 20, include_issues: bool = True) -> pd.DataFrame:
    """生成不良事件数据 (AE Domain)"""
    np.random.seed(100)

    ae_terms = [
        "Headache", "Nausea", "Dizziness", "Fatigue", "Rash",
        "Hypertension", "Diarrhea", "Constipation", "Insomnia", "Cough",
        "Back pain", "Arthralgia", "Pyrexia", "Vomiting", "Anemia",
        "Leukopenia", "Thrombocytopenia", "ALT increased", "AST increased", "Hypokalemia"
    ]

    ae_sev = ["MILD", "MODERATE", "SEVERE", "DEATH"]
    ae_rel = ["NOT RELATED", "POSSIBLE", "PROBABLE", "DEFINITE"]
    ae_out = ["RECOVERED/RESOLVED", "RECOVERING/RESOLVING", "NOT RECOVERED/NOT RESOLVED",
              "RECOVERED/RESOLVED WITH SEQUELAE", "FATAL", "UNKNOWN"]

    n_ae = n_subjects * 3  # 平均每人 3 个 AE
    data = {
        "STUDYID": ["STUDY001"] * n_ae,
        "DOMAIN": ["AE"] * n_ae,
        "USUBJID": np.random.choice(
            [f"STUDY001-SITE001-{i+1:04d}" for i in range(n_subjects)], n_ae
        ),
        "AETERM": np.random.choice(ae_terms, n_ae),
        "AEDECOD": np.random.choice(ae_terms, n_ae),
        "AEBODSYS": np.random.choice(
            ["Nervous system", "Gastrointestinal", "General", "Skin", "Blood", "Metabolism"],
            n_ae
        ),
        "AESEV": np.random.choice(ae_sev, n_ae, p=[0.5, 0.3, 0.15, 0.05]),
        "AESER": np.random.choice(["Y", "N", "N", "N"], n_ae),
        "AEREL": np.random.choice(ae_rel, n_ae, p=[0.3, 0.4, 0.2, 0.1]),
        "AEOUT": np.random.choice(ae_out, n_ae),
        "AESTDTC": [f"2024-{np.random.randint(1,13):02d}-{np.random.randint(1,28):02d}" for _ in range(n_ae)],
        "AEENDTC": [""] * n_ae,
    }

    df = pd.DataFrame(data)

    # 计算 AEENDTC
    for i in range(len(df)):
        from datetime import datetime, timedelta
        start = datetime.strptime(df.at[i, "AESTDTC"], "%Y-%m-%d")
        end = start + timedelta(days=np.random.randint(1, 30))
        df.at[i, "AEENDTC"] = end.strftime("%Y-%m-%d")

    if include_issues:
        # 日期逻辑错误
        df.loc[0, "AESTDTC"] = "2024-11-01"
        df.loc[0, "AEENDTC"] = "2024-10-01"

        # AESEV 错误值
        df.loc[1, "AESEV"] = "CRITICAL"

        # 缺失 AESTDTC
        df.loc[2, "AESTDTC"] = None

    return df


def generate_vs_dataset(n_subjects: int = 20, include_issues: bool = True) -> pd.DataFrame:
    """生成生命体征数据 (VS Domain)"""
    np.random.seed(200)

    n_records = n_subjects * 5  # 每人 5 次测量
    data = {
        "STUDYID": ["STUDY001"] * n_records,
        "DOMAIN": ["VS"] * n_records,
        "USUBJID": np.random.choice(
            [f"STUDY001-SITE001-{i+1:04d}" for i in range(n_subjects)], n_records
        ),
        "VS_DTC": [f"2024-{np.random.randint(1,13):02d}-{np.random.randint(1,28):02d}" for _ in range(n_records)],
        "VSTEST": np.random.choice(
            ["Systolic Blood Pressure", "Diastolic Blood Pressure", "Heart Rate",
             "Temperature", "Respiratory Rate"],
            n_records
        ),
        "VSORRESU": np.random.choice(["mmHg", "mmHg", "beats/min", "C", "breaths/min"], n_records),
    }

    df = pd.DataFrame(data)

    # 根据测试项目生成结果
    results = []
    for test in df["VSTEST"]:
        if test == "Systolic Blood Pressure":
            results.append(round(np.random.normal(120, 15), 0))
        elif test == "Diastolic Blood Pressure":
            results.append(round(np.random.normal(80, 10), 0))
        elif test == "Heart Rate":
            results.append(round(np.random.normal(72, 10), 0))
        elif test == "Temperature":
            results.append(round(np.random.normal(36.5, 0.5), 1))
        elif test == "Respiratory Rate":
            results.append(round(np.random.normal(16, 3), 0))

    df["VSORRES"] = results

    if include_issues:
        # 异常生命体征
        df.loc[0, "VSORRES"] = 250  # 收缩压异常
        df.loc[1, "VSORRES"] = 45   # 心率过低

        # 温度非数值
        df.loc[2, "VSORRES"] = "HIGH"

    return df


def generate_all_samples(output_dir: str):
    """生成所有示例数据集"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("生成示例数据...")

    # DM 数据集
    dm = generate_dm_dataset(n_subjects=30, include_issues=True)
    dm_path = output_dir / "sample_dm_data.csv"
    dm.to_csv(dm_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ DM 数据: {dm_path} ({len(dm)} 行)")

    # AE 数据集
    ae = generate_ae_dataset(n_subjects=20, include_issues=True)
    ae_path = output_dir / "sample_ae_data.csv"
    ae.to_csv(ae_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ AE 数据: {ae_path} ({len(ae)} 行)")

    # VS 数据集
    vs = generate_vs_dataset(n_subjects=20, include_issues=True)
    vs_path = output_dir / "sample_vs_data.csv"
    vs.to_csv(vs_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ VS 数据: {vs_path} ({len(vs)} 行)")

    # 合并完整测试集
    all_data_path = output_dir / "sample_clinical_data.csv"
    combined = pd.concat([dm, ae, vs], ignore_index=True)
    combined.to_csv(all_data_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ 完整数据集: {all_data_path} ({len(combined)} 行)")

    # Excel 格式
    with pd.ExcelWriter(output_dir / "sample_clinical_data.xlsx", engine="openpyxl") as writer:
        dm.to_excel(writer, sheet_name="DM", index=False)
        ae.to_excel(writer, sheet_name="AE", index=False)
        vs.to_excel(writer, sheet_name="VS", index=False)
    print(f"  ✓ Excel 数据: {output_dir / 'sample_clinical_data.xlsx'}")

    print(f"\n所有示例数据已生成至: {output_dir.resolve()}")


if __name__ == "__main__":
    generate_all_samples(Path(__file__).parent)
