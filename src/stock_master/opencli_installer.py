from __future__ import annotations

import argparse
import shutil
from importlib import resources
from pathlib import Path
from typing import Iterable

DEFAULT_SOURCE_SUBDIR = 'stock_master/opencli_clis'


def _iter_yaml_files(root: Path) -> Iterable[Path]:
    return sorted(path for path in root.rglob('*.yaml') if path.is_file())


def install_opencli_clis(target_dir: str | Path, source_dir: str | Path | None = None) -> list[Path]:
    target_root = Path(target_dir).expanduser().resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    if source_dir is not None:
        source_root = Path(source_dir).expanduser().resolve()
    else:
        source_root = Path(resources.files('stock_master').joinpath('opencli_clis'))

    installed: list[Path] = []
    for src in _iter_yaml_files(source_root):
        relative = src.relative_to(source_root)
        dest = target_root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() or dest.is_symlink():
            if dest.is_dir() and not dest.is_symlink():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        dest.symlink_to(src)
        installed.append(dest)
    return installed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Symlink bundled OpenCLI YAML commands into a target directory.')
    parser.add_argument('--target-dir', default='~/.opencli/clis', help='Where to create symlinks (default: ~/.opencli/clis)')
    parser.add_argument('--source-dir', help='Override source directory for YAML files (for development/testing)')
    parser.add_argument('--quiet', action='store_true', help='Suppress per-file output; only print final summary')
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    installed = install_opencli_clis(args.target_dir, args.source_dir)
    if not args.quiet:
        for path in installed:
            print(path)
    print(f'linked {len(installed)} opencli command files into {Path(args.target_dir).expanduser()}')
    return 0


__all__ = ['DEFAULT_SOURCE_SUBDIR', 'install_opencli_clis', 'build_parser', 'main']
