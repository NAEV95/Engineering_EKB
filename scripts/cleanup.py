#!/usr/bin/env python3
"""
Cleanup script for ProMut-MD.
Removes old files and figures while preserving code functionality.
"""

import os
import sys
import argparse
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cleanup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def find_files_to_clean(directory, pattern=None, older_than_days=30, dry_run=True, keep_n_newest=2):
    """Find files to clean based on pattern and age"""
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return []
    
    logger.info(f"Scanning directory: {directory}")
    files = list(Path(directory).glob("**/*" + (pattern or "")))
    
    # Filter by age
    if older_than_days > 0:
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        aged_files = [f for f in files if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff_date]
    else:
        aged_files = [f for f in files if f.is_file()]
    
    # Group files by type/pattern if needed
    if keep_n_newest > 0 and pattern:
        # Group by parent directory
        by_dir = {}
        for f in aged_files:
            parent = str(f.parent)
            if parent not in by_dir:
                by_dir[parent] = []
            by_dir[parent].append(f)
        
        # For each directory, sort files by modification time and keep newest N
        files_to_remove = []
        for parent, files_list in by_dir.items():
            sorted_files = sorted(files_list, key=lambda f: f.stat().st_mtime, reverse=True)
            if len(sorted_files) > keep_n_newest:
                files_to_remove.extend(sorted_files[keep_n_newest:])
    else:
        files_to_remove = aged_files
    
    # Log what would be deleted
    if files_to_remove:
        if dry_run:
            logger.info(f"Would delete {len(files_to_remove)} files from {directory}" + 
                       (f" matching {pattern}" if pattern else ""))
        else:
            logger.info(f"Will delete {len(files_to_remove)} files from {directory}" + 
                       (f" matching {pattern}" if pattern else ""))
        
        # Log the first 10 files
        for f in files_to_remove[:10]:
            logger.info(f"  {f}")
        if len(files_to_remove) > 10:
            logger.info(f"  ...and {len(files_to_remove) - 10} more files")
    else:
        logger.info(f"No files to delete in {directory}" + 
                   (f" matching {pattern}" if pattern else ""))
    
    return files_to_remove

def clean_files(files_to_remove, dry_run=True):
    """Remove files from the list"""
    if not files_to_remove:
        logger.info("No files to clean")
        return
    
    if dry_run:
        logger.info(f"Would have deleted {len(files_to_remove)} files (dry run)")
        return
    
    # Actually delete files
    deleted_count = 0
    error_count = 0
    for f in files_to_remove:
        try:
            os.remove(f)
            deleted_count += 1
        except Exception as e:
            logger.error(f"Error deleting {f}: {str(e)}")
            error_count += 1
    
    logger.info(f"Deleted {deleted_count} files successfully")
    if error_count > 0:
        logger.warning(f"Failed to delete {error_count} files")

def cleanup_repository(args):
    """Main cleanup function"""
    logger.info("Starting repository cleanup")
    
    # Track all files to clean
    all_files_to_clean = []
    
    # Find temporary files to clean
    if args.clean_temp:
        temp_patterns = [".tmp", ".temp", ".log", ".bak"]
        for pattern in temp_patterns:
            temp_files = find_files_to_clean(".", pattern, args.days, args.dry_run, 0)
            all_files_to_clean.extend(temp_files)
    
    # Clean processed data
    if args.clean_processed:
        processed_files = find_files_to_clean(
            "data/processed", 
            ".csv", 
            args.days, 
            args.dry_run, 
            args.keep
        )
        all_files_to_clean.extend(processed_files)
    
    # Clean results
    if args.clean_results:
        results_files = find_files_to_clean(
            "data/results", 
            ".json", 
            args.days, 
            args.dry_run, 
            args.keep
        )
        all_files_to_clean.extend(results_files)
    
    # Clean models
    if args.clean_models:
        model_files = find_files_to_clean(
            "models", 
            ".pkl", 
            args.days, 
            args.dry_run, 
            args.keep
        )
        all_files_to_clean.extend(model_files)
    
    # Clean figures
    if args.clean_figures:
        figure_extensions = [".png", ".jpg", ".jpeg", ".pdf", ".svg", ".eps", ".html"]
        for ext in figure_extensions:
            figure_files = find_files_to_clean(
                "figures", 
                ext, 
                args.days, 
                args.dry_run, 
                args.keep
            )
            all_files_to_clean.extend(figure_files)
    
    # Actually delete files
    clean_files(all_files_to_clean, args.dry_run)
    
    logger.info("Cleanup completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Clean up old files and figures')
    parser.add_argument('--dry-run', action='store_true', 
                      help='Only show what would be deleted without actually deleting')
    parser.add_argument('--days', type=int, default=30,
                      help='Delete files older than this many days (default: 30)')
    parser.add_argument('--keep', type=int, default=2,
                      help='Keep this many newest files of each type (default: 2)')
    parser.add_argument('--clean-temp', action='store_true',
                      help='Clean temporary files (.tmp, .temp, etc.)')
    parser.add_argument('--clean-processed', action='store_true',
                      help='Clean old processed data files')
    parser.add_argument('--clean-results', action='store_true',
                      help='Clean old results files')
    parser.add_argument('--clean-models', action='store_true',
                      help='Clean old model files')
    parser.add_argument('--clean-figures', action='store_true',
                      help='Clean old figure files')
    parser.add_argument('--clean-all', action='store_true',
                      help='Clean all categories of files')
    
    args = parser.parse_args()
    
    # If clean-all is specified, enable all cleaning options
    if args.clean_all:
        args.clean_temp = True
        args.clean_processed = True
        args.clean_results = True
        args.clean_models = True
        args.clean_figures = True
    
    # If no specific cleaning option is specified, show help
    if not (args.clean_temp or args.clean_processed or args.clean_results or 
            args.clean_models or args.clean_figures):
        parser.print_help()
        print("\nError: No cleaning option specified. Please specify what to clean.")
        sys.exit(1)
    
    cleanup_repository(args) 