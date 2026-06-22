"""Generate final validation and completeness report."""
from __future__ import annotations

import json
import csv
import zipfile
from pathlib import Path
from datetime import datetime


def main() -> int:
    """Generate comprehensive validation report."""
    
    publish_dir = Path('artifacts/publish_files')
    configs_dir = Path('artifacts/configs')
    docs_dir = Path('docs')
    
    # Read simulation results
    with open(docs_dir / 'simulation_summary.json', 'r', encoding='utf-8') as f:
        sim_summary = json.load(f)
    
    # Read index
    with open(publish_dir / 'index.json', 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    # Read config
    with open(configs_dir / 'config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Build validation report
    report = {
        'timestamp': datetime.now().isoformat(),
        'package_name': 'Azteck_plinko_set',
        'version': '1.0.0',
        'game_modes': {
            'total': len(index['modes']),
            'validation_status': sim_summary['all_modes_pass'],
            'passed': sim_summary['passed'],
            'failed': sim_summary['total_modes'] - sim_summary['passed'],
        },
        'constraints': {
            'rtp_target': 0.9605,
            'rtp_tolerance': 0.01,
            'volatility_target': 3.0,
            'volatility_min': 0.6,
            'volatility_max': 50.0,
            'payout_scale': 100.0,
        },
        'artifacts': {
            'lookup_csvs': len([f for f in publish_dir.glob('lookUpTable_*.csv')]),
            'books_files': len([f for f in publish_dir.glob('books_*.jsonl.zst')]),
            'config_entries': len(config.get('bookShelfConfig', [])),
            'total_files_publish_zip': 74,
        },
        'modes_by_difficulty': {},
        'modes_by_rows': {},
    }
    
    # Count by difficulty and rows
    for mode in index['modes']:
        diff = mode.get('difficulty', 'Unknown')
        rows = mode.get('rows', 0)
        
        if diff not in report['modes_by_difficulty']:
            report['modes_by_difficulty'][diff] = 0
        report['modes_by_difficulty'][diff] += 1
        
        if rows not in report['modes_by_rows']:
            report['modes_by_rows'][rows] = 0
        report['modes_by_rows'][rows] += 1
    
    # Per-mode details
    report['mode_details'] = []
    for result in sim_summary['results']:
        report['mode_details'].append({
            'mode': result['mode'],
            'theoretical_rtp': result['theoretical_rtp'],
            'empirical_rtp': result['empirical_rtp'],
            'empirical_std': result['empirical_std'],
            'max_payout': result['max_payout'],
            'status': 'PASS' if result['pass'] else 'FAIL',
        })
    
    # Zip validation
    zips = {
        'Azteck_plinko_set_publish.zip': 'Flat-root for Stake Engine upload',
        'Azteck_plinko_set_full.zip': 'Full development package',
    }
    
    report['zips'] = {}
    for zip_name, description in zips.items():
        zip_path = Path(zip_name)
        if zip_path.exists():
            with zipfile.ZipFile(zip_path, 'r') as zf:
                report['zips'][zip_name] = {
                    'description': description,
                    'size_mb': zip_path.stat().st_size / 1024 / 1024,
                    'file_count': len(zf.namelist()),
                }
    
    # Save report
    report_path = docs_dir / 'validation_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f'Validation Report Summary:')
    print(f'  Package: {report["package_name"]}')
    print(f'  Total Modes: {report["game_modes"]["total"]}')
    print(f'  Validation Status: {"PASS" if report["game_modes"]["validation_status"] else "FAIL"}')
    print(f'  Passed: {report["game_modes"]["passed"]}/{report["game_modes"]["total"]}')
    print(f'  Modes by Difficulty: {report["modes_by_difficulty"]}')
    print(f'  Modes by Rows: {report["modes_by_rows"]}')
    print(f'  Zips Created: {len(report["zips"])}')
    print(f'  Saved: {report_path}')
    
    return 0 if report['game_modes']['validation_status'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
