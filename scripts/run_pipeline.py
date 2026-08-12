#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


SYS_HELLO = 454


def run(cmd, cwd=None, capture=False):
    shown = " ".join(str(x) for x in cmd)
    print(f"+ {shown}")
    if capture:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.stdout:
            print(result.stdout, end="")
    else:
        result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def require(path, description):
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"missing {description}: {path}")
    return path


def write_dummy_syscall(path):
    text = f"""#include <unistd.h>
#include <sys/syscall.h>

#define SYS_hello {SYS_HELLO}

void dummy_syscall(int libcallno)
{{
    (void)syscall(SYS_hello, libcallno);
}}
"""
    path.write_text(text)


def extract_expected_ids(ir_path):
    text = Path(ir_path).read_text()
    return [
        int(x)
        for x in re.findall(
            r"call\s+void\s+@dummy_syscall\(i32\s+(\d+)\)",
            text,
        )
    ]


def verify_instrumented_ir(ir_path):
    text = Path(ir_path).read_text()

    numbered = re.findall(r"dummy_syscall\.\d+", text)
    if numbered:
        raise SystemExit(
            "instrumentation still contains duplicate symbols: "
            + ", ".join(sorted(set(numbered)))
        )

    expected = extract_expected_ids(ir_path)
    if not expected:
        raise SystemExit("no dummy_syscall instrumentation found in IR")

    if "declare void @dummy_syscall(i32)" not in text:
        raise SystemExit("missing declaration: declare void @dummy_syscall(i32)")

    print("instrumented syscall IDs:", expected)
    return expected


def extract_policy_start(policy_path):
    text = Path(policy_path).read_text()
    match = re.search(r"start:(\d+)", text)
    if not match:
        raise SystemExit(
            f"{policy_path} has no start:<node> marker; "
            "apply the LLVM start-node patch and rebuild opt"
        )
    return int(match.group(1))


def host(args):
    repo = Path(args.repo).expanduser().resolve()
    tests = repo / "tests"
    llvm_build = Path(args.llvm_build).expanduser().resolve()

    clang = require(llvm_build / "bin" / "clang", "custom clang")
    opt = require(llvm_build / "bin" / "opt", "custom opt")
    source = require(
        Path(args.source).expanduser()
        if args.source
        else tests / "test.c",
        "test source",
    )

    tests.mkdir(parents=True, exist_ok=True)

    ll = tests / "test.ll"
    instrumented = tests / "test.instrumented.ll"
    wrapper = tests / "dummy_syscall.c"
    binary = tests / f"ex{args.ex}"
    graph = tests / "graph.dot"
    policy = tests / f"secure_policy_{args.ex}.dot"

    write_dummy_syscall(wrapper)
    print(f"wrote {wrapper}")

    run(
        [
            str(clang),
            "-O0",
            "-Xclang",
            "-disable-O0-optnone",
            "-fno-builtin",
            "-S",
            "-emit-llvm",
            str(source),
            "-o",
            str(ll),
        ],
        cwd=tests,
    )

    run(
        [
            str(opt),
            "-passes=helloworld",
            "-S",
            str(ll),
            "-o",
            str(instrumented),
        ],
        cwd=tests,
    )

    expected = verify_instrumented_ir(instrumented)

    require(graph, "graph.dot produced by LLVM pass")
    start = extract_policy_start(graph)
    shutil.copy2(graph, policy)

    run(
        [
            str(clang),
            "-O0",
            str(instrumented),
            str(wrapper),
            "-o",
            str(binary),
        ],
        cwd=tests,
    )

    print()
    print("HOST BUILD COMPLETE")
    print(f"binary:  {binary}")
    print(f"policy:  {policy}")
    print(f"start:   {start}")
    print(f"IDs:     {expected}")
    print()
    print("Do not run this binary on the host.")
    print("Run the guest stage inside QEMU after the project 9P share is mounted.")


def wait_for_ready(log_path, process, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if log_path.exists():
            text = log_path.read_text(errors="replace")
            if "TIME(s)" in text:
                return
        code = process.poll()
        if code is not None:
            text = log_path.read_text(errors="replace") if log_path.exists() else ""
            raise SystemExit(
                f"monitor exited before becoming ready, code={code}\n{text}"
            )
        time.sleep(0.2)

    text = log_path.read_text(errors="replace") if log_path.exists() else ""
    raise SystemExit(f"monitor did not become ready in time\n{text}")


def guest(args):
    project = Path(args.project).resolve()
    tests = project / "tests"
    monitor_src = project / "monitor"

    binary_src = require(tests / f"ex{args.ex}", "instrumented guest binary")
    policy_src = require(
        tests / f"secure_policy_{args.ex}.dot",
        "generated policy",
    )
    ir_src = require(tests / "test.instrumented.ll", "instrumented IR")
    monitor_py = require(monitor_src / "monitor.py", "monitor.py")
    text2graph_py = require(monitor_src / "text2graph.py", "text2graph.py")

    expected = extract_expected_ids(ir_src)
    start = extract_policy_start(policy_src)

    work = Path(args.workdir).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)

    binary = work / f"ex{args.ex}"
    policy = work / f"secure_policy_{args.ex}.dot"
    log = work / "monitor.log"

    shutil.copy2(binary_src, binary)
    shutil.copy2(policy_src, policy)
    shutil.copy2(monitor_py, work / "monitor.py")
    shutil.copy2(text2graph_py, work / "text2graph.py")
    binary.chmod(binary.stat().st_mode | 0o111)

    if log.exists():
        log.unlink()

    print(f"policy start node: {start}")
    print(f"expected LLVM IDs: {expected}")

    monitor_cmd = [
        "sudo",
        "timeout",
        "--signal=INT",
        str(args.timeout),
        "python3",
        "-u",
        "monitor.py",
    ]

    print("+ " + " ".join(monitor_cmd))
    with log.open("w") as log_file:
        process = subprocess.Popen(
            monitor_cmd,
            cwd=work,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

        wait_for_ready(log, process, args.ready_timeout)
        print("MONITOR READY")

        result = run([str(binary)], cwd=work, capture=True)
        time.sleep(args.post_delay)

        try:
            process.wait(timeout=max(1, args.timeout))
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=3)

    text = log.read_text(errors="replace")
    print()
    print("===== monitor.log =====")
    print(text, end="" if text.endswith("\n") else "\n")
    print("=======================")

    observed = [
        int(x)
        for x in re.findall(r"Syscall argument value:\s*(\d+)", text)
    ]

    print(f"expected IDs: {expected}")
    print(f"observed IDs: {observed}")

    if observed[: len(expected)] != expected:
        raise SystemExit(
            "pipeline mismatch: observed syscall sequence does not match LLVM IR"
        )

    print()
    print("PIPELINE PASS")
    print("LLVM instrumentation -> dummy syscall -> custom kernel -> BCC -> NFA worked.")


def main():
    parser = argparse.ArgumentParser(
        description="Automate the libcall-sandbox host build and QEMU guest test."
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    host_p = sub.add_parser("host", help="build and instrument on the host")
    host_p.add_argument(
        "--repo",
        default="~/sandbox",
        help="project repository root",
    )
    host_p.add_argument(
        "--llvm-build",
        default="~/llvm-work/llvm-project-20/build",
        help="LLVM build directory containing bin/clang and bin/opt",
    )
    host_p.add_argument(
        "--source",
        default=None,
        help="C source file; defaults to <repo>/tests/test.c",
    )
    host_p.add_argument("--ex", type=int, default=1, help="example number")
    host_p.set_defaults(func=host)

    guest_p = sub.add_parser("guest", help="run the end-to-end test inside QEMU")
    guest_p.add_argument(
        "--project",
        default="/mnt/project",
        help="9P-mounted project root",
    )
    guest_p.add_argument(
        "--workdir",
        default="~/monitor-test",
        help="writable guest working directory",
    )
    guest_p.add_argument("--ex", type=int, default=1, help="example number")
    guest_p.add_argument(
        "--timeout",
        type=int,
        default=12,
        help="monitor timeout in seconds",
    )
    guest_p.add_argument(
        "--ready-timeout",
        type=int,
        default=10,
        help="seconds to wait for monitor startup",
    )
    guest_p.add_argument(
        "--post-delay",
        type=float,
        default=1.0,
        help="seconds to allow BPF events to drain after ex1 exits",
    )
    guest_p.set_defaults(func=guest)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
