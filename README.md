# libcall-sandbox

Compiler-assisted Linux process sandbox using statically extracted
library-call control-flow policies.

## Architecture

```text
C program
    |
    v
LLVM IR
    |
    v
Custom LLVM Module Pass
    |
    +----> libc-call policy graph
    |
    +----> instrumented LLVM IR
              |
              v
        dummy_syscall(ID)
              |
              v
        Linux kernel
              |
              v
          eBPF/BCC
              |
              v
       NFA policy monitor
```

## Current status

The LLVM component has been restored and tested with LLVM 20.1.0.

The LLVM pass:

- performs module-level LLVM IR analysis
- identifies libc calls
- constructs an interprocedural library-call graph
- represents control-flow transitions using epsilon edges
- exports the policy in Graphviz DOT format
- inserts `dummy_syscall(ID)` before recognized libc calls

The Linux kernel syscall and eBPF/BCC runtime components are being
restored next.

## LLVM modifications

Modified source files are available under `llvm/`.

A reproducible patch is available at:

```text
patches/llvm20-libcall-sandbox.patch
```

Apply it from the root of an LLVM 20.1.0 source tree:

```bash
patch -p1 --dry-run < /path/to/llvm20-libcall-sandbox.patch
patch -p1 < /path/to/llvm20-libcall-sandbox.patch
```
