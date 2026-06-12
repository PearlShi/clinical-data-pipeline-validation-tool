"""
Streamlit Web 界面
================
提供用户上传数据文件、选择校验/转换功能、配置参数、查看处理进度与结果报告。
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import tempfile
import os
import logging

# 将项目根目录加入 sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.data_loader import DataLoader
from src.validation.validator import Validator
from src.validation.report import ReportGenerator
from src.conversion.converter import DataConverter
from src.scripts.clean_data import DataCleaner
from src.scripts.stats_checks import StatisticalChecker
from src.scripts.outlier_detection import OutlierDetector
from src.config.settings import config

logger = logging.getLogger(__name__)


# ============================
# 页面配置
# ============================
st.set_page_config(
    page_title="临床数据 Pipeline 自动化校验工具",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================
# 会话状态初始化
# ============================
if "df" not in st.session_state:
    st.session_state.df = None
if "file_name" not in st.session_state:
    st.session_state.file_name = None
if "validation_results" not in st.session_state:
    st.session_state.validation_results = None
if "validation_summary" not in st.session_state:
    st.session_state.validation_summary = None


# ============================
# 辅助函数
# ============================
def load_data(uploaded_file):
    """加载上传的数据文件"""
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=Path(uploaded_file.name).suffix
    ) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        loader = DataLoader(tmp_path)
        df = loader.load()
        st.session_state.df = df
        st.session_state.file_name = uploaded_file.name
        os.unlink(tmp_path)
        return df
    except Exception as e:
        os.unlink(tmp_path)
        st.error(f"数据加载失败: {e}")
        return None


def run_validation(df):
    """执行数据校验"""
    validator = Validator()
    results = validator.validate(df)
    summary = validator.get_summary()
    st.session_state.validation_results = results
    st.session_state.validation_summary = summary
    return results, summary


# ============================
# 侧边栏 — 导航
# ============================
st.sidebar.title("🏥 临床数据校验工具")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "功能导航",
    [
        "📤 数据上传与预览",
        "🔍 数据质量校验",
        "🔄 格式转换 (→SDTM)",
        "🧹 数据清洗",
        "📊 统计分析",
        "⚠️ 离群值检测",
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 关于")
st.sidebar.info(
    "本工具用于临床试验数据的质量校验、"
    "SDTM 格式转换与批量处理。"
    "\n\n遵循 CDISC 标准规范。"
    "\n\n版本: v1.0.0"
)


# ============================
# 页面内容
# ============================

# ---- 页面1: 数据上传与预览 ----
if page == "📤 数据上传与预览":
    st.title("📤 数据上传与预览")
    st.markdown("上传 CSV 或 Excel 格式的临床数据文件，查看数据预览与基本信息。")

    uploaded_file = st.file_uploader(
        "选择数据文件",
        type=["csv", "xlsx", "xls"],
        help="支持 CSV、Excel (.xlsx/.xls) 格式的临床数据文件"
    )

    if uploaded_file is not None:
        if st.button("📂 加载数据", type="primary"):
            with st.spinner("正在加载数据..."):
                df = load_data(uploaded_file)

        if st.session_state.df is not None:
            df = st.session_state.df

            # 基本信息
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("文件", st.session_state.file_name)
            col2.metric("行数", len(df))
            col3.metric("列数", len(df.columns))
            col4.metric("内存", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")

            # 数据预览
            st.subheader("数据预览")
            st.dataframe(df.head(100), use_container_width=True)

            # 列信息
            st.subheader("列信息")
            col_info = pd.DataFrame({
                "列名": df.columns,
                "类型": [str(df[c].dtype) for c in df.columns],
                "非空数": [df[c].notna().sum() for c in df.columns],
                "缺失数": [df[c].isna().sum() for c in df.columns],
                "缺失率(%)": [round(df[c].isna().sum() / len(df) * 100, 2) for c in df.columns],
                "唯一值数": [df[c].nunique() for c in df.columns],
            })
            st.dataframe(col_info, use_container_width=True)

            # 描述统计
            with st.expander("查看数值列描述统计"):
                numeric_cols = df.select_dtypes(include="number").columns
                if len(numeric_cols) > 0:
                    st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                else:
                    st.info("没有数值列")

    else:
        # 示例数据说明
        st.info("👆 请上传数据文件开始使用")
        st.markdown("""
        **支持的数据格式:**
        - CSV (UTF-8 编码)
        - Excel (.xlsx / .xls)

        **数据要求:**
        - 推荐包含 SDTM 标准变量（如 USUBJID, STUDYID, DOMAIN 等）
        - 日期格式推荐: YYYY-MM-DD
        """)

# ---- 页面2: 数据质量校验 ----
elif page == "🔍 数据质量校验":
    st.title("🔍 数据质量校验")
    st.markdown("对临床数据执行全面的质量校验，包括变量完整性、数据类型、异常值、CDISC 合规性检查。")

    if st.session_state.df is None:
        st.warning("请先在「数据上传与预览」页面上传数据文件。")
    else:
        df = st.session_state.df

        st.info(f"当前数据: **{st.session_state.file_name}** ({len(df)} 行 × {len(df.columns)} 列)")

        col1, col2 = st.columns([1, 4])
        with col1:
            run_btn = st.button("🚀 开始校验", type="primary", use_container_width=True)
        with col2:
            if st.session_state.validation_results is not None:
                st.success("已有校验结果，点击重新校验")

        if run_btn or st.session_state.validation_results is not None:
            if run_btn:
                with st.spinner("正在执行校验检查..."):
                    results, summary = run_validation(df)

            results = st.session_state.validation_results
            summary = st.session_state.validation_summary

            # 整体状态
            st.subheader("校验结果")

            status_color = {
                "PASSED": ("✅ 通过", "green"),
                "WARNING": ("⚠️ 警告", "orange"),
                "FAILED": ("❌ 未通过", "red"),
            }
            status_text, status_c = status_color.get(summary.overall_status, ("未知", "gray"))
            st.markdown(f"<h3 style='color:{status_c};'>{status_text}</h3>",
                       unsafe_allow_html=True)

            # 摘要指标
            mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
            mcol1.metric("检查项", summary.total_checks)
            mcol2.metric("✅ 通过", summary.passed)
            mcol3.metric("❌ 未通过", summary.failed)
            mcol4.metric("🔴 错误", summary.errors)
            mcol5.metric("🟡 警告", summary.warnings)

            # 详细结果
            tab_labels = [f"{'❌' if not r.passed else '✅'} {r.check_name[:20]} ({r.issue_count})"
                         for r in results]
            tabs = st.tabs(tab_labels)

            for i, (tab, result) in enumerate(zip(tabs, results)):
                with tab:
                    st.markdown(f"**检查状态**: {'✅ 通过' if result.passed else '❌ 未通过'}")
                    st.markdown(f"**检查记录数**: {result.total_checked}")
                    st.markdown(f"**发现问题**: {result.issue_count}")

                    if result.issues:
                        # 问题表格
                        issues_data = [{
                            "严重级别": issue.severity,
                            "描述": issue.description[:80] + "..." if len(issue.description) > 80 else issue.description,
                            "变量": issue.column or "",
                            "行号": issue.row_index if issue.row_index else "",
                            "实际值": str(issue.actual_value)[:30] if issue.actual_value else "",
                            "修改建议": issue.suggestion[:50] + "..." if issue.suggestion and len(issue.suggestion) > 50 else (issue.suggestion or ""),
                        } for issue in result.issues[:200]]
                        df_issues = pd.DataFrame(issues_data)
                        st.dataframe(df_issues, use_container_width=True)

                        if len(result.issues) > 200:
                            st.warning(f"仅显示前 200 条问题，共 {len(result.issues)} 条")

            # 下载报告
            st.subheader("📥 下载校验报告")
            col1, col2 = st.columns(2)
            with col1:
                report_gen = ReportGenerator(
                    title=f"临床数据校验报告 - {st.session_state.file_name}"
                )
                md_content = report_gen.generate_markdown(results, summary)

                st.download_button(
                    label="📄 下载 Markdown 报告",
                    data=md_content,
                    file_name=f"validation_report_{st.session_state.file_name.rsplit('.', 1)[0]}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with col2:
                # 导出到临时 Excel
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp_path = tmp.name
                report_gen.generate_excel(results, summary, tmp_path)
                with open(tmp_path, "rb") as f:
                    excel_data = f.read()
                os.unlink(tmp_path)

                st.download_button(
                    label="📊 下载 Excel 报告",
                    data=excel_data,
                    file_name=f"validation_report_{st.session_state.file_name.rsplit('.', 1)[0]}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

# ---- 页面3: 格式转换 ----
elif page == "🔄 格式转换 (→SDTM)":
    st.title("🔄 格式转换 → SDTM")
    st.markdown("将原始临床数据自动转换为 SDTM 标准格式。")

    if st.session_state.df is None:
        st.warning("请先在「数据上传与预览」页面上传数据文件。")
    else:
        df = st.session_state.df
        st.info(f"当前数据: **{st.session_state.file_name}** ({len(df)} 行 × {len(df.columns)} 列)")

        with st.expander("转换配置", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                study_id = st.text_input("研究编号 (STUDYID)", value="STUDY001")
                domain = st.text_input("数据域 (DOMAIN)", value="DM",
                                       help="如 DM, AE, VS, LB, EX 等")
            with col2:
                output_format = st.selectbox("输出格式", ["xlsx", "csv"], index=0)
                normalize_dates = st.checkbox("标准化日期格式", value=True)
                normalize_categorical = st.checkbox("标准化分类变量", value=True)

        if st.button("🔄 开始转换", type="primary"):
            with st.spinner("正在执行格式转换..."):
                try:
                    converter = DataConverter(
                        study_id=study_id,
                        domain=domain,
                    )

                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=Path(st.session_state.file_name).suffix or ".csv"
                    ) as tmp:
                        tmp_path = tmp.name
                        if st.session_state.file_name.endswith(('.xlsx', '.xls')):
                            df.to_excel(tmp_path, index=False)
                        else:
                            df.to_csv(tmp_path, index=False, encoding='utf-8-sig')

                    with tempfile.TemporaryDirectory() as tmp_dir:
                        result = converter.convert(
                            input_path=tmp_path,
                            output_dir=tmp_dir,
                            output_format=output_format,
                            normalize_dates=normalize_dates,
                            normalize_categorical=normalize_categorical,
                        )

                        os.unlink(tmp_path)

                        st.success("✅ 格式转换成功!")

                        # 显示结果
                        col1, col2, col3 = st.columns(3)
                        col1.metric("输出行数", result["rows"])
                        col2.metric("输出列数", result["columns"])
                        col3.metric("变量映射", result["variables_mapped"])

                        # 显示转换日志
                        log = result.get("log")
                        if log:
                            st.subheader("转换日志")
                            st.text(log.to_text())

                        # 提供下载转换后数据
                        output_path = result["output_file"]
                        with open(output_path, "rb") as f:
                            file_data = f.read()

                        output_ext = Path(output_path).suffix
                        st.download_button(
                            label=f"📥 下载转换后数据 ({output_ext})",
                            data=file_data,
                            file_name=f"{domain.lower()}_sdtm{output_ext}",
                            use_container_width=True,
                        )

                except Exception as e:
                    st.error(f"转换失败: {e}")
                    logger.exception("转换出错")

# ---- 页面4: 数据清洗 ----
elif page == "🧹 数据清洗":
    st.title("🧹 数据清洗")
    st.markdown("对临床数据进行常用清洗操作：去重、去除空白、标记缺失值、统一大小写等。")

    if st.session_state.df is None:
        st.warning("请先在「数据上传与预览」页面上传数据文件。")
    else:
        df = st.session_state.df
        st.info(f"当前数据: **{st.session_state.file_name}** ({len(df)} 行 × {len(df.columns)} 列)")

        with st.expander("清洗选项", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                do_dedup = st.checkbox("去除重复行", value=True)
                do_strip = st.checkbox("去除字符串空白", value=True)
                do_mark_na = st.checkbox("标记常见缺失值", value=True)
            with col2:
                do_case = st.checkbox("统一大写", value=True)
                do_fill = st.checkbox("填充缺失值", value=False)
                fill_strategy = st.selectbox(
                    "填充策略",
                    ["auto", "mean", "median", "mode", "drop"],
                    index=0,
                    disabled=not do_fill,
                )

        if st.button("🧹 执行清洗", type="primary"):
            with st.spinner("正在清洗数据..."):
                try:
                    cleaned_df = DataCleaner.clean_and_prepare(
                        df,
                        drop_duplicates=do_dedup,
                        strip_whitespace=do_strip,
                        mark_missing=do_mark_na,
                        standardize_case=do_case,
                        fill_missing=do_fill,
                        fill_strategy=fill_strategy,
                    )

                    st.subheader("清洗结果")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("原行数", len(df))
                    col2.metric("清洗后行数", len(cleaned_df))
                    col3.metric("减少", len(df) - len(cleaned_df))

                    # 前后对比
                    tab1, tab2 = st.tabs(["清洗后数据", "变更详情"])
                    with tab1:
                        st.dataframe(cleaned_df.head(100), use_container_width=True)
                        st.caption(f"共 {len(cleaned_df)} 行，显示前 100 行")

                    with tab2:
                        changes = []
                        for col in df.columns:
                            orig_null = df[col].isna().sum()
                            new_null = cleaned_df[col].isna().sum() if col in cleaned_df.columns else orig_null
                            if orig_null != new_null:
                                changes.append({
                                    "列名": col,
                                    "原缺失数": orig_null,
                                    "清洗后缺失数": new_null,
                                    "变化": new_null - orig_null,
                                })
                        if changes:
                            st.dataframe(pd.DataFrame(changes), use_container_width=True)
                        else:
                            st.info("缺失值无变化")

                    # 提供下载
                    output_path = Path(tempfile.gettempdir()) / "cleaned_data.xlsx"
                    cleaned_df.to_excel(output_path, index=False)
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="📥 下载清洗后数据",
                            data=f,
                            file_name=f"cleaned_{st.session_state.file_name.rsplit('.', 1)[0]}.xlsx",
                            use_container_width=True,
                        )

                except Exception as e:
                    st.error(f"清洗失败: {e}")

# ---- 页面5: 统计分析 ----
elif page == "📊 统计分析":
    st.title("📊 统计分析")
    st.markdown("对临床数据进行描述性统计、分布分析与交叉表分析。")

    if st.session_state.df is None:
        st.warning("请先在「数据上传与预览」页面上传数据文件。")
    else:
        df = st.session_state.df
        st.info(f"当前数据: **{st.session_state.file_name}** ({len(df)} 行 × {len(df.columns)} 列)")

        tab1, tab2, tab3 = st.tabs(["📋 描述统计", "📈 分布分析", "🔗 交叉表分析"])

        with tab1:
            if st.button("生成描述统计", type="primary"):
                with st.spinner("正在计算..."):
                    desc = StatisticalChecker.describe_dataset(df)

                    # 数值列统计
                    if desc["numeric_summary"]:
                        st.subheader("数值列统计")
                        stats_df = pd.DataFrame(desc["numeric_summary"]).T
                        st.dataframe(stats_df, use_container_width=True)

                    # 分类列统计
                    if desc["categorical_summary"]:
                        st.subheader("分类列统计")
                        for col, info in list(desc["categorical_summary"].items())[:10]:
                            with st.expander(f"{col} (唯一值: {info['unique_values']})"):
                                cnt_df = pd.DataFrame(
                                    list(info["top_values"].items()),
                                    columns=["取值", "频数"]
                                )
                                cnt_df["占比(%)"] = (cnt_df["频数"] / df[col].notna().sum() * 100).round(2)
                                st.dataframe(cnt_df, use_container_width=True)

                    # 缺失值
                    st.subheader("缺失值概览")
                    missing_df = pd.DataFrame({
                        "列名": list(desc["missing_percent"].keys()),
                        "缺失数": list(desc["missing_summary"].values()),
                        "缺失率(%)": list(desc["missing_percent"].values()),
                    }).sort_values("缺失率(%)", ascending=False)
                    st.dataframe(missing_df[missing_df["缺失数"] > 0], use_container_width=True)

        with tab2:
            col_options = df.select_dtypes(include="number").columns
            if len(col_options) > 0:
                selected_col = st.selectbox("选择数值列", col_options)
                expected_min = st.number_input("期望最小值（可选）", value=0.0)
                expected_max = st.number_input("期望最大值（可选）", value=300.0)

                if st.button("分析分布", type="primary"):
                    with st.spinner("正在分析..."):
                        dist = StatisticalChecker.check_value_distribution(
                            df, selected_col,
                            expected_min=expected_min if expected_min else None,
                            expected_max=expected_max if expected_max else None,
                        )

                        if "error" in dist:
                            st.error(dist["error"])
                        else:
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("均值", f"{dist['mean']:.2f}")
                            m2.metric("中位数", f"{dist['median']:.2f}")
                            m3.metric("标准差", f"{dist['std']:.2f}")
                            m4.metric("样本量", dist["count"])

                            col1, col2 = st.columns(2)
                            with col1:
                                st.subheader("百分位数")
                                pct_df = pd.DataFrame(
                                    list(dist["percentiles"].items()),
                                    columns=["百分位", "值"]
                                )
                                st.dataframe(pct_df, use_container_width=True)

                            with col2:
                                if "normality_test" in dist:
                                    nt = dist["normality_test"]
                                    st.subheader("正态性检验")
                                    st.metric("统计量", f"{nt['statistic']:.4f}")
                                    st.metric("p值", f"{nt['p_value']:.4f}")
                                    st.write("结论:", "✅ 正态分布" if nt["is_normal"] else "❌ 非正态分布")
            else:
                st.warning("数据中没有数值列")

        with tab3:
            cat_cols = df.select_dtypes(include=["object", "category"]).columns
            if len(cat_cols) >= 2:
                row_var = st.selectbox("行变量", cat_cols, key="row_var")
                col_var = st.selectbox("列变量", cat_cols, key="col_var")

                if st.button("生成交叉表", type="primary"):
                    with st.spinner("正在计算..."):
                        ct = StatisticalChecker.cross_tabulation(df, row_var, col_var)
                        if "error" in ct:
                            st.error(ct["error"])
                        else:
                            st.subheader("交叉表（计数）")
                            ct_df = pd.DataFrame(ct["table"])
                            st.dataframe(ct_df, use_container_width=True)

                            if "chi_square_test" in ct:
                                chi = ct["chi_square_test"]
                                st.subheader("卡方检验")
                                m1, m2, m3 = st.columns(3)
                                m1.metric("卡方值", f"{chi['chi2_statistic']:.4f}")
                                m2.metric("p值", f"{chi['p_value']:.4f}")
                                m3.metric("自由度", chi["degrees_of_freedom"])
                                st.write("结论:", "✅ 显著相关" if chi.get("significant") else "❌ 无显著相关")
            else:
                st.warning("需要至少 2 个分类变量进行交叉表分析")

# ---- 页面6: 离群值检测 ----
elif page == "⚠️ 离群值检测":
    st.title("⚠️ 离群值检测")
    st.markdown("使用多种统计方法识别临床数据中的异常值。")

    if st.session_state.df is None:
        st.warning("请先在「数据上传与预览」页面上传数据文件。")
    else:
        df = st.session_state.df
        st.info(f"当前数据: **{st.session_state.file_name}** ({len(df)} 行 × {len(df.columns)} 列)")

        col1, col2 = st.columns(2)
        with col1:
            method = st.selectbox(
                "检测方法",
                ["iqr (IQR四分位距法)", "zscore (Z-Score法)", "mad (MAD绝对中位差法)", "all (综合投票法)"],
                index=0,
            )
            method_key = method.split(" ")[0]
        with col2:
            threshold = st.number_input(
                "阈值",
                min_value=0.5, max_value=10.0, value=3.0, step=0.5,
                help="IQR: 倍数(默认1.5), Z-Score: 标准差倍数(默认3), MAD: 倍数(默认3.5)"
            )

        # 选择列
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        selected_cols = st.multiselect(
            "选择要检测的列（不选则检测所有数值列）",
            numeric_cols,
            default=numeric_cols[:min(5, len(numeric_cols))],
        )

        # 分组选项
        group_opts = st.multiselect(
            "分组列（可选，按组别分别检测）",
            [c for c in ["DOMAIN", "STUDYID", "ARM", "VISIT", "SEX"] if c in df.columns],
        )

        if st.button("🔍 检测离群值", type="primary"):
            target_cols = selected_cols if selected_cols else None

            with st.spinner("正在检测离群值..."):
                try:
                    threshold_map = {"iqr": 1.5, "zscore": 3.0, "mad": 3.5}
                    effective_threshold = threshold_map.get(method_key, threshold)

                    results = OutlierDetector.detect_outliers(
                        df,
                        columns=target_cols,
                        method=method_key,
                        threshold=effective_threshold if method_key != "all" else 3.0,
                        groupby=group_opts if group_opts else None,
                    )

                    if not results:
                        st.success("✅ 未检测到离群值")
                    else:
                        # 汇总表
                        summary_df = OutlierDetector.get_outlier_summary(results, df)
                        st.subheader("离群值汇总")
                        st.dataframe(summary_df, use_container_width=True)

                        # 详细结果
                        st.subheader("详细离群值信息")
                        for col, result_df in results.items():
                            outlier_count = result_df["_is_outlier"].sum()
                            if outlier_count > 0:
                                with st.expander(f"📊 {col} — {outlier_count} 个离群值"):
                                    merged = pd.concat([df.loc[result_df.index], result_df], axis=1)
                                    outliers = merged[merged["_is_outlier"] == True]
                                    display_cols = [col, "_outlier_severity"]
                                    if "_zscore" in result_df.columns:
                                        display_cols.append("_zscore")
                                    if "_mad_score" in result_df.columns:
                                        display_cols.append("_mad_score")
                                    if "_votes" in result_df.columns:
                                        display_cols.append("_votes")
                                    st.dataframe(outliers[display_cols], use_container_width=True)

                except Exception as e:
                    st.error(f"离群值检测失败: {e}")


# ============================
# 页脚
# ============================
st.sidebar.markdown("---")
st.sidebar.markdown(
    "<small>临床数据 Pipeline 自动化校验工具 v1.0.0</small>",
    unsafe_allow_html=True,
)
