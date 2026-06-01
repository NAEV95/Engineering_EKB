#!/usr/bin/env python3
"""Command-line interface for ProMut-MD workflows."""

import argparse
import sys


def build_parser():
    parser = argparse.ArgumentParser(
        prog="promut-md",
        description="ProMut-MD workflow runner",
    )
    subparsers = parser.add_subparsers(dest="command")

    pipeline = subparsers.add_parser("pipeline", help="Run the full MD-to-ML pipeline")
    pipeline.add_argument("--config", default="config/default.yml")
    pipeline.add_argument("--skip-md", action="store_true")
    pipeline.add_argument("--skip-features", action="store_true")
    pipeline.add_argument("--skip-training", action="store_true")
    pipeline.add_argument("--skip-evaluation", action="store_true")
    pipeline.add_argument("--skip-visualization", action="store_true")
    pipeline.add_argument("--output-dir")

    no_mds = subparsers.add_parser("no-mds", help="Run the precomputed-feature pipeline")
    no_mds.add_argument("--data-dir", default="data")
    no_mds.add_argument("--output-dir", default="output")
    no_mds.add_argument("--config", default="config/default.yml")
    no_mds.add_argument("--random-seed", type=int, default=42)
    no_mds.add_argument("--optuna-trials", type=int, default=100)
    no_mds.add_argument("--skip-optuna", action="store_true")
    no_mds.add_argument("--skip-bootstrap", action="store_true")
    no_mds.add_argument("--bootstrap-iterations", type=int, default=1000)
    no_mds.add_argument("--compare-with-ddmut", action="store_true")

    excel = subparsers.add_parser("excel", help="Run the Excel mutation workflow")
    excel.add_argument("--excel", required=True)
    excel.add_argument("--sheet", default=0)
    excel.add_argument("--config", default="config/excel_workflow.yml")
    excel.add_argument("--output-dir", default="data/processed")
    excel.add_argument("--no-figures", action="store_true")

    build_mutants = subparsers.add_parser("build-mutants", help="Build point-mutant PDB structures")
    build_mutants.add_argument("--wild-type-pdb", required=True)
    build_mutants.add_argument("--mutations", required=True)
    build_mutants.add_argument("--output-dir", required=True)
    build_mutants.add_argument("--backend", choices=["foldx", "simple"], default="foldx")
    build_mutants.add_argument("--foldx-bin", default=None)

    cleanup = subparsers.add_parser("cleanup", help="Clean generated artifacts")
    cleanup.add_argument("--dry-run", action="store_true")
    cleanup.add_argument("--days", type=int, default=30)
    cleanup.add_argument("--keep", type=int, default=2)
    cleanup.add_argument("--clean-temp", action="store_true")
    cleanup.add_argument("--clean-processed", action="store_true")
    cleanup.add_argument("--clean-results", action="store_true")
    cleanup.add_argument("--clean-models", action="store_true")
    cleanup.add_argument("--clean-figures", action="store_true")
    cleanup.add_argument("--clean-all", action="store_true")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "pipeline":
        from scripts.run_pipeline import main as pipeline_main

        forwarded = ["--config", args.config]
        for flag in [
            "skip_md",
            "skip_features",
            "skip_training",
            "skip_evaluation",
            "skip_visualization",
        ]:
            if getattr(args, flag):
                forwarded.append("--" + flag.replace("_", "-"))
        if args.output_dir:
            forwarded.extend(["--output-dir", args.output_dir])
        old_argv = sys.argv
        try:
            sys.argv = ["run_pipeline.py", *forwarded]
            pipeline_main()
        finally:
            sys.argv = old_argv
        return 0

    if args.command == "no-mds":
        from run_pipeline_no_mds import main as no_mds_main

        no_mds_main(args)
        return 0

    if args.command == "excel":
        from scripts.excel_workflow import main as excel_main

        old_argv = sys.argv
        forwarded = [
            "--excel",
            args.excel,
            "--sheet",
            str(args.sheet),
            "--config",
            args.config,
            "--output-dir",
            args.output_dir,
        ]
        if args.no_figures:
            forwarded.append("--no-figures")
        try:
            sys.argv = ["excel_workflow.py", *forwarded]
            return excel_main()
        finally:
            sys.argv = old_argv

    if args.command == "build-mutants":
        from scripts.structure_generation.build_mutants import build_mutant_structures

        try:
            build_mutant_structures(args.wild_type_pdb, args.mutations, args.output_dir, args.backend, args.foldx_bin)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            parser.error(str(exc))
        return 0

    if args.command == "cleanup":
        from scripts.cleanup import cleanup_repository

        if args.clean_all:
            args.clean_temp = True
            args.clean_processed = True
            args.clean_results = True
            args.clean_models = True
            args.clean_figures = True
        cleanup_repository(args)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
