"""Build publish zip for Azteck Plinko Set."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path


def main() -> int:
    """Build flat-root publish zip for Stake Engine."""
    
    publish_dir = Path('artifacts/publish_files')
    configs_dir = Path('artifacts/configs')
    
    # Read index
    with open(publish_dir / 'index.json', 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    # Create publish zip (flat structure at root)
    zip_path = Path('Azteck_plinko_set_publish.zip')
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add index.json at root
        zf.write(publish_dir / 'index.json', 'index.json')
        
        # Add all lookup CSVs at root
        for mode in index['modes']:
            lookup_file = mode['weights']
            src_path = publish_dir / lookup_file
            zf.write(src_path, lookup_file)
        
        # Add all books files at root
        for mode in index['modes']:
            books_file = mode['events']
            src_path = publish_dir / books_file
            zf.write(src_path, books_file)

        # Add per-mode force files and standard force file
        for mode in index['modes']:
            force_file = f"force_record_{mode['name']}.json"
            src_path = publish_dir / force_file
            if src_path.exists():
                zf.write(src_path, force_file)
        standard_force = publish_dir / 'force.json'
        if standard_force.exists():
            zf.write(standard_force, 'force.json')
        
        # Add config.json at root
        zf.write(configs_dir / 'config.json', 'config.json')

        # Add frontend config at root when present
        fe_cfg = configs_dir / 'fe_config.json'
        if fe_cfg.exists():
            zf.write(fe_cfg, 'fe_config.json')
    
    # Count entries
    with zipfile.ZipFile(zip_path, 'r') as zf:
        file_list = zf.namelist()
        count = len(file_list)
    
    print(f'Created {zip_path} with {count} files')
    print(f'Zip size: {zip_path.stat().st_size / 1024 / 1024:.2f} MB')
    
    # Also create full development zip (nested structure)
    full_zip_path = Path('Azteck_plinko_set_full.zip')
    added_arcs: set[str] = set()

    with zipfile.ZipFile(full_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add all files with relative paths (skip duplicates)
        for root_dir, dirs, files in Path('artifacts').walk():
            for file in files:
                file_path = Path(root_dir) / file
                arcname = str(file_path.relative_to(Path('.'))).replace('\\', '/')
                if arcname not in added_arcs:
                    zf.write(file_path, arcname)
                    added_arcs.add(arcname)

        # Add docs
        for doc_file in Path('docs').glob('*'):
            arcname = str(doc_file.relative_to(Path('.'))).replace('\\', '/')
            if arcname not in added_arcs:
                zf.write(doc_file, arcname)
                added_arcs.add(arcname)
    
    print(f'Created {full_zip_path}')
    print(f'Zip size: {full_zip_path.stat().st_size / 1024 / 1024:.2f} MB')
    
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
