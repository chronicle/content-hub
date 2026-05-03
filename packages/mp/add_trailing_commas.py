#!/usr/bin/env python3
"""Script to automatically add trailing commas to multiline function calls.

This prevents formatters like `ruff format` or `Black` from collapsing
multiline argument lists into a single line.
"""

import argparse
from pathlib import Path

import libcst as cst
from libcst.metadata import PositionProvider


class AddTrailingCommaTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if not updated_node.args:
            return updated_node

        pos = self.get_metadata(PositionProvider, original_node)
        is_multiline = pos.start.line != pos.end.line

        if is_multiline:
            last_arg = updated_node.args[-1]
            if isinstance(last_arg.comma, cst.MaybeSentinel) or last_arg.comma is None:
                new_args = list(updated_node.args)
                new_args[-1] = last_arg.with_changes(comma=cst.Comma())
                return updated_node.with_changes(args=tuple(new_args))

        return updated_node


def process_file(file_path: Path) -> bool:
    """Process a single file and add trailing commas to multiline calls."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = cst.parse_module(content)
        wrapper = cst.metadata.MetadataWrapper(tree)
        transformer = AddTrailingCommaTransformer()
        modified_tree = wrapper.visit(transformer)

        if modified_tree.code != content:
            file_path.write_text(modified_tree.code, encoding="utf-8")
            print(f"Added trailing commas to: {file_path}")
            return True
    except cst.ParserSyntaxError as e:
        print(f"Skipping {file_path}: Syntax Error - {e}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Add trailing commas to multiline calls.")
    parser.add_argument("paths", nargs="+", type=Path, help="Files or directories to process.")
    args = parser.parse_args()

    # Expand directories to find all .py files
    files_to_process = []
    for path in args.paths:
        if path.is_file() and path.suffix == ".py":
            files_to_process.append(path)
        elif path.is_dir():
            files_to_process.extend(path.rglob("*.py"))

    print(f"Found {len(files_to_process)} Python files to process.")
    modified_count = 0
    for file_path in files_to_process:
        if process_file(file_path):
            modified_count += 1

    print(f"\nDone. Modified {modified_count} files.")


if __name__ == "__main__":
    main()
