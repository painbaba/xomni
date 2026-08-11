/* Unaligned 32-bit load micro-repro for aarch64 semantics testing.
 * Compile: aarch64-linux-gnu-gcc -static -O1 unaligned_microrepro.c -o misaligned_arm
 * Run:    qemu-aarch64 ./misaligned_arm
 * Expected on aarch64 Linux (SCTLR.A=0): ALL offsets load successfully, rc=0.
 * If a platform faults, you get SIGBUS / "Illegal instruction" instead.
 */
#include <stdio.h>
#include <stdint.h>

volatile uint32_t sink;

int main(void)
{
    uint8_t buf[4096];
    for (int i = 0; i < 4096; i++)
        buf[i] = (uint8_t)i;
    for (int off = 0; off < 8; off++)
    {
        uint32_t v = *(uint32_t *)(buf + off);
        sink = v;
        printf("off=%d v=0x%08x\n", off, v);
    }
    return 0;
}
