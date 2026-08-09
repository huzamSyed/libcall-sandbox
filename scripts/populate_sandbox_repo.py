#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
REPO = HOME / "sandbox"
LLVM_TREE = HOME / "llvm-work" / "llvm-project-20"
TEST_FILE = HOME / "llvm-work" / "test-sandbox" / "test.c"

LLVM_CPP = LLVM_TREE / "llvm/lib/Transforms/Utils/HelloWorld.cpp"
LLVM_H = LLVM_TREE / "llvm/include/llvm/Transforms/Utils/HelloWorld.h"

PATCH_INPUTS = [
    "llvm/lib/Transforms/Utils/HelloWorld.cpp",
    "llvm/include/llvm/Transforms/Utils/HelloWorld.h",
    "llvm/lib/Passes/PassRegistry.def",
]


def run(cmd, cwd=None, capture=False):
    print("+", " ".join(map(str, cmd)), flush=True)
    result = subprocess.run(
        list(map(str, cmd)),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if result.returncode != 0:
        if capture:
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
        raise RuntimeError(f"command failed with exit code {result.returncode}")
    return result


def require_file(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"missing file: {path}")
    return path


def copy_file(src, dst):
    src = require_file(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"[+] copied {src} -> {dst}", flush=True)


def write_project_files():
    gitignore = (
        "*.ll\n"
        "*.bc\n"
        "graph.dot\n"
        "*.png\n"
        "*.svg\n"
        "build/\n"
        "cmake-build-*/\n"
        "__pycache__/\n"
        "*.pyc\n"
        "*.o\n"
        "*.ko\n"
        "*.mod\n"
        "*.cmd\n"
        "*.order\n"
        "*.symvers\n"
        "*.img\n"
        "*.qcow2\n"
        "*.iso\n"
        ".vscode/\n"
        ".idea/\n"
        "*.swp\n"
        "*~\n"
    )

    readme = (
        "# libcall-sandbox\n\n"
        "Compiler-assisted Linux process sandbox using statically extracted "
        "library-call control-flow policies.\n\n"
        "## Current status\n\n"
        "The LLVM side has been restored and tested with LLVM 20.1.0.\n\n"
        "The custom LLVM module pass identifies libc calls, builds an "
        "interprocedural library-call policy graph, emits the graph in "
        "Graphviz DOT format, and inserts `dummy_syscall(ID)` before "
        "recognized libc calls.\n\n"
        "The Linux kernel syscall and eBPF/BCC runtime monitor are the next "
        "components to be restored.\n\n"
        "## Repository layout\n\n"
        "- `llvm/` - modified LLVM pass source\n"
        "- `patches/llvm20-libcall-sandbox.patch` - patch against LLVM 20.1.0\n"
        "- `monitor/` - original BCC/eBPF monitor and graph parser\n"
        "- `tests/` - small LLVM-pass test program\n\n"
        "## Applying the LLVM patch\n\n"
        "From the root of a clean LLVM 20.1.0 source tree:\n\n"
        "```bash\n"
        "patch -p1 --dry-run < /path/to/llvm20-libcall-sandbox.patch\n"
        "patch -p1 < /path/to/llvm20-libcall-sandbox.patch\n"
        "```\n"
    )

    (REPO / ".gitignore").write_text(gitignore)
    (REPO / "README.md").write_text(readme)


def generate_patch():
    result = run(
        ["git", "diff", "llvmorg-20.1.0", "--", *PATCH_INPUTS],
        cwd=LLVM_TREE,
        capture=True,
    )
    if not result.stdout.strip():
        raise RuntimeError(
            "LLVM patch is empty; expected changes relative to llvmorg-20.1.0"
        )

    patch_path = REPO / "patches/llvm20-libcall-sandbox.patch"
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(result.stdout)
    print(f"[+] generated {patch_path}", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Populate ~/sandbox with the restored libcall-sandbox checkpoint."
    )
    parser.add_argument("--monitor", required=True, help="path to monitor.py")
    parser.add_argument(
        "--text2graph",
        required=True,
        help="path to txt2gprah.py or text2graph.py",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="push the resulting main branch to origin",
    )
    args = parser.parse_args()

    monitor = require_file(args.monitor)
    text2graph = require_file(args.text2graph)

    if not REPO.is_dir() or not (REPO / ".git").is_dir():
        raise RuntimeError(f"{REPO} is not an initialized Git repository")
    if not LLVM_TREE.is_dir():
        raise RuntimeError(f"LLVM tree missing: {LLVM_TREE}")

    require_file(LLVM_CPP)
    require_file(LLVM_H)
    require_file(TEST_FILE)

    print("=== Populating repository ===", flush=True)

    copy_file(LLVM_CPP, REPO / "llvm/HelloWorld.cpp")
    copy_file(LLVM_H, REPO / "llvm/HelloWorld.h")
    copy_file(monitor, REPO / "monitor/monitor.py")
    copy_file(text2graph, REPO / "monitor/text2graph.py")
    copy_file(TEST_FILE, REPO / "tests/test.c")

    generate_patch()
    write_project_files()

    print("\n=== Files ===", flush=True)
    run(["find", ".", "-maxdepth", "3", "-type", "f"], cwd=REPO)

    print("\n=== Creating first checkpoint commit ===", flush=True)
    run(
        [
            "git",
            "add",
            ".gitignore",
            "README.md",
            "llvm",
            "patches",
            "monitor",
            "tests",
        ],
        cwd=REPO,
    )
    run(["git", "status", "--short"], cwd=REPO)

    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=REPO,
    )
    if staged.returncode == 0:
        raise RuntimeError("nothing was staged; no commit was created")

    run(
        [
            "git",
            "commit",
            "-m",
            "Restore LLVM library-call sandbox instrumentation",
        ],
        cwd=REPO,
    )

    run(["git", "branch", "-M", "main"], cwd=REPO)

    if args.push:
        print("\n=== Pushing to GitHub ===", flush=True)
        run(["git", "push", "-u", "origin", "main"], cwd=REPO)

    print("\n=== Done ===", flush=True)
    run(["git", "log", "--oneline", "-1"], cwd=REPO)

    if not args.push:
        print("\nInspect the repository, then push with:")
        print("  cd ~/sandbox")
        print("  git push -u origin main")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)
