"""
命令行工具入口
===========
基于 Click 框架，支持通过参数指定数据文件、校验规则、输出路径等，
一键执行全流程处理。
"""

import click
import sys
import logging
from pathlib import Path
from typing import Optional

# 将项目根目录加入 sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.data_loader import DataLoader, BatchDataLoader
from src.validation.validator import Validator
from src.validation.report import ReportGenerator
from src.conversion.converter import DataConverter
from src.config.settings import config, PROJECT_ROOT


# 配置日志
def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ============================
# 通用选项
# ============================
def common_options(f):
    f = click.option(
        "-o", "--output-dir", default=None,
        help="输出目录（默认: data/output）"
    )(f)
    f = click.option(
        "-v", "--verbose", is_flag=True, help="显示详细日志"
    )(f)
    return f


# ============================
# validate 命令
# ============================
@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "-r", "--rules", default=None,
    help="校验规则配置文件路径（可选，使用默认规则）"
)
@click.option(
    "--report-name", default="validation_report",
    help="报告文件名（不含扩展名）"
)
@click.option(
    "--md-only", is_flag=True,
    help="仅生成 Markdown 报告（不生成 Excel）"
)
@common_options
def validate(input_file, output_dir, rules, report_name, md_only, verbose):
    """
    对临床数据文件执行质量校验

    INPUT_FILE 为输入数据文件路径（支持 CSV / Excel）
    """
    setup_logging(verbose)
    click.echo(click.style("=" * 60, fg="cyan"))
    click.echo(click.style("  临床数据校验工具 — 数据格式校验", fg="cyan", bold=True))
    click.echo(click.style("=" * 60, fg="cyan"))

    # 确定输出目录
    out_dir = Path(output_dir) if output_dir else config.report_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # 加载数据
    click.echo(f"\n📂 加载数据: {input_file}")
    try:
        loader = DataLoader(input_file)
        df = loader.load()
        click.echo(f"   ✓ 数据加载成功: {len(df)} 行 × {len(df.columns)} 列")
        click.echo(f"   ✓ 列名: {', '.join(df.columns[:10])}")
        if len(df.columns) > 10:
            click.echo(f"     ... 及其他 {len(df.columns) - 10} 列")
    except Exception as e:
        click.echo(click.style(f"✗ 数据加载失败: {e}", fg="red"), err=True)
        sys.exit(1)

    # 执行校验
    click.echo("\n🔍 执行校验检查...")
    validator = Validator()
    with click.progressbar(
        validator.checkers,
        label="运行检查器",
        item_show_func=lambda c: c.check_name if c else ""
    ) as checkers:
        for checker in checkers:
            pass  # 进度条逻辑
    results = validator.validate(df)
    summary = validator.get_summary()

    # 显示结果摘要
    click.echo(f"\n📊 校验摘要:")
    click.echo(f"  检查项: {summary.total_checks} | "
               f"✅ 通过: {summary.passed} | "
               f"❌ 未通过: {summary.failed}")
    click.echo(f"  问题总数: {summary.total_issues} | "
               f"🔴 错误: {summary.errors} | "
               f"🟡 警告: {summary.warnings}")

    if summary.overall_status == "PASSED":
        click.echo(click.style(f"\n✓ 整体状态: 通过", fg="green", bold=True))
    elif summary.overall_status == "WARNING":
        click.echo(click.style(f"\n⚠ 整体状态: 警告", fg="yellow", bold=True))
    else:
        click.echo(click.style(f"\n✗ 整体状态: 未通过", fg="red", bold=True))

    # 生成报告
    click.echo("\n📝 生成校验报告...")
    report_gen = ReportGenerator(
        title=f"临床数据校验报告 - {Path(input_file).name}"
    )

    if md_only:
        md_content = report_gen.generate_markdown(results, summary)
        report_paths = config.save_report(md_content, str(out_dir), report_name)
        click.echo(f"  ✓ Markdown 报告: {report_paths['markdown']}")
    else:
        report_paths = report_gen.generate_all(
            results, summary, str(out_dir), report_name
        )
        click.echo(f"  ✓ Markdown 报告: {report_paths['markdown']}")
        click.echo(f"  ✓ Excel 报告:   {report_paths['excel']}")

    click.echo(click.style(f"\n✓ 校验完成!", fg="green", bold=True))


# ============================
# convert 命令
# ============================
@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--study-id", default=None, help="研究编号")
@click.option("--domain", default=None, help="数据域（如 DM, AE, VS）")
@click.option("--output-format", type=click.Choice(["csv", "xlsx"]), default="xlsx", help="输出格式")
@click.option("--no-date-norm", is_flag=True, help="跳过日期标准化")
@click.option("--no-category-norm", is_flag=True, help="跳过分类变量标准化")
@common_options
def convert(input_file, output_dir, study_id, domain, output_format,
            no_date_norm, no_category_norm, verbose):
    """
    将原始临床数据转换为 SDTM 标准格式

    INPUT_FILE 为输入数据文件路径（支持 CSV / Excel）
    """
    setup_logging(verbose)
    click.echo(click.style("=" * 60, fg="cyan"))
    click.echo(click.style("  临床数据校验工具 — 格式转换", fg="cyan", bold=True))
    click.echo(click.style("=" * 60, fg="cyan"))

    out_dir = Path(output_dir) if output_dir else config.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"\n📂 加载数据: {input_file}")

    try:
        converter = DataConverter(
            study_id=study_id,
            domain=domain,
        )
        result = converter.convert(
            input_path=input_file,
            output_dir=str(out_dir),
            output_format=output_format,
            normalize_dates=not no_date_norm,
            normalize_categorical=not no_category_norm,
        )
    except Exception as e:
        click.echo(click.style(f"✗ 转换失败: {e}", fg="red"), err=True)
        sys.exit(1)

    # 显示结果
    click.echo(f"\n✓ 转换成功!")
    click.echo(f"  输出文件: {result['output_file']}")
    click.echo(f"  数据维度: {result['rows']} 行 × {result['columns']} 列")
    click.echo(f"  变量映射: {result['variables_mapped']} 个")

    summary = result.get("summary", {})
    click.echo(f"  总步骤数: {summary.get('total_steps', 0)}")
    click.echo(f"  耗时: {summary.get('duration_seconds', 0):.2f} 秒")

    # 显示日志路径
    log_dir = out_dir / "logs"
    if log_dir.exists():
        log_files = list(log_dir.glob("*conversion*"))
        if log_files:
            click.echo(f"  日志文件: {log_files[0]}")

    click.echo(click.style(f"\n✓ 转换完成!", fg="green", bold=True))


# ============================
# batch 命令
# ============================
@click.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--mode", type=click.Choice(["validate", "convert", "both"]),
              default="validate", help="处理模式")
@click.option("--study-id", default=None, help="研究编号（转换模式时使用）")
@click.option("--domain", default=None, help="数据域（转换模式时使用）")
@click.option("--output-format", type=click.Choice(["csv", "xlsx"]), default="xlsx")
@common_options
def batch(input_dir, output_dir, mode, study_id, domain, output_format, verbose):
    """
    对目录中的多个数据文件批量执行校验/转换

    INPUT_DIR 为数据文件所在目录
    """
    setup_logging(verbose)
    click.echo(click.style("=" * 60, fg="cyan"))
    click.echo(click.style("  临床数据校验工具 — 批量处理", fg="cyan", bold=True))
    click.echo(click.style("=" * 60, fg="cyan"))

    out_dir = Path(output_dir) if output_dir else config.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # 列出文件
    loader = BatchDataLoader(input_dir)
    files = loader.list_files()
    if not files:
        click.echo(click.style(f"✗ 目录中无支持的数据文件", fg="red"), err=True)
        sys.exit(1)

    click.echo(f"\n📂 发现 {len(files)} 个数据文件:")
    for f in files:
        click.echo(f"  - {f.name}")

    # 批量处理
    results = {"success": 0, "failed": 0, "details": []}

    for file_path in files:
        click.echo(f"\n{'=' * 40}")
        click.echo(f"处理: {file_path.name}")
        click.echo(f"{'=' * 40}")

        try:
            df = DataLoader(str(file_path)).load()

            if mode in ("validate", "both"):
                validator = Validator()
                v_results = validator.validate(df)
                v_summary = validator.get_summary()
                report_gen = ReportGenerator(title=f"校验报告 - {file_path.name}")
                file_out = out_dir / f"{file_path.stem}_validation_report.xlsx"
                report_gen.generate_excel(v_results, v_summary, str(file_out))
                click.echo(f"  ✓ 校验完成: {v_summary.total_issues} 个问题")

            if mode in ("convert", "both"):
                converter = DataConverter(study_id=study_id, domain=domain)
                conv_result = converter.convert(
                    input_path=str(file_path),
                    output_dir=str(out_dir / "converted"),
                    output_format=output_format,
                )
                click.echo(f"  ✓ 转换完成: {conv_result['output_file']}")

            results["success"] += 1
            results["details"].append({"file": file_path.name, "status": "SUCCESS"})

        except Exception as e:
            click.echo(click.style(f"  ✗ 失败: {e}", fg="red"))
            results["failed"] += 1
            results["details"].append({"file": file_path.name, "status": "FAILED", "error": str(e)})

    # 汇总
    click.echo(f"\n{'=' * 40}")
    click.echo(click.style("批量处理完成", fg="green", bold=True))
    click.echo(f"  成功: {results['success']} | 失败: {results['failed']}")
    click.echo(f"  输出目录: {out_dir}")


# ============================
# summary 命令
# ============================
@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@common_options
def summary(input_file, output_dir, verbose):
    """
    显示数据文件的概要统计信息

    INPUT_FILE 为输入数据文件路径
    """
    setup_logging(verbose)
    click.echo(click.style("=" * 60, fg="cyan"))
    click.echo(click.style("  临床数据校验工具 — 数据概要", fg="cyan", bold=True))
    click.echo(click.style("=" * 60, fg="cyan"))

    try:
        loader = DataLoader(input_file)
        df, preview = loader.load_with_preview()
    except Exception as e:
        click.echo(click.style(f"✗ 加载失败: {e}", fg="red"), err=True)
        sys.exit(1)

    # 基本信息
    click.echo(f"\n📋 基本信息:")
    click.echo(f"  文件名: {preview['file_name']}")
    click.echo(f"  文件大小: {preview['file_size'] / 1024:.1f} KB")
    click.echo(f"  行数: {preview['rows']}")
    click.echo(f"  列数: {preview['columns']}")
    click.echo(f"  内存占用: {preview['memory_usage'] / 1024:.1f} KB")

    # 列信息
    click.echo(f"\n📊 列信息:")
    for col, dtype in preview["dtypes"].items():
        missing = preview["missing_counts"].get(col, 0)
        missing_pct = missing / preview["rows"] * 100 if preview["rows"] > 0 else 0
        click.echo(f"  {col:20s} | {dtype:15s} | 缺失: {missing:4d} ({missing_pct:5.1f}%)")


# ============================
# 主 CLI 入口
# ============================
@click.group()
@click.version_option(version="1.0.0", message="临床数据校验工具 v1.0.0")
def cli():
    """
    临床数据 Pipeline 自动化校验工具

    用于临床试验数据的质量校验、SDTM 格式转换与批量处理。
    支持 CSV/Excel 数据文件，遵循 CDISC 标准规范。
    """
    pass


cli.add_command(validate)
cli.add_command(convert)
cli.add_command(batch)
cli.add_command(summary)


if __name__ == "__main__":
    cli()
