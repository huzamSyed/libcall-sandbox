#!/bin/bash
set -e

qemu-system-x86_64 \
    -m 2G \
    -smp 2 \
    -kernel "$HOME/kernel-work/linux/arch/x86/boot/bzImage" \
    -drive file="$HOME/kernel-work/ubuntu-rootfs.img",format=raw,if=virtio \
    -append "root=/dev/vda rw console=ttyS0" \
    -nic user,model=e1000 \
    -virtfs local,path="$HOME/kernel-work/linux",mount_tag=kernel,security_model=none,readonly=on \
    -virtfs local,path="$HOME/sandbox",mount_tag=project,security_model=none,readonly=on \
    -nographic
