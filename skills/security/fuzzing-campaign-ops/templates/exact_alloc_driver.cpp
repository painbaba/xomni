// Exact-allocation repro driver (generic, any libFuzzer harness).
// Purpose: distinguish "known bug is ASAN-invisible due to input-buffer slack"
// from "bug actually fixed". libFuzzer's input buffer carries capacity slack,
// so small OOB READS past the logical end stay inside the allocation and ASAN
// never fires. malloc(n) EXACTLY removes that slack: if the bug still doesn't
// fire here, it's a harness-path issue (e.g. a decodeHeader phase consuming
// short inputs) or genuinely fixed — NOT a buffer-slack artifact.
//
// Build (libavc example, on the VM; adapt harness/sources per library):
//   clang++ -O1 -g -msse4.1 -fsanitize=address,fuzzer-no-link -fno-omit-frame-pointer \
//     exact_alloc_driver.cpp -x c++ libavc/fuzzer/avc_dec_fuzzer_nodbg.cpp \
//     -x c libavc/decoder/*.c libavc/common/*.c libavc/decoder/x86/*.c libavc/common/x86/*.c \
//     -I libavc -I libavc/decoder -I libavc/common -I libavc/fuzzer \
//     -I libavc/common/x86 -I libavc/decoder/x86 -o exact_alloc_test
// Run: ./exact_alloc_test <input.bin>   → rc=0 + "decode returned 0" = no ASAN hit.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s file\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("fopen"); return 2; }
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    // exact-size allocation, NO padding
    uint8_t *buf = (uint8_t *)malloc((size_t)n);
    if (!buf) { perror("malloc"); return 2; }
    size_t got = fread(buf, 1, (size_t)n, f);
    fclose(f);
    fprintf(stderr, "read %zu bytes into exact %zu-byte heap alloc\n", got, (size_t)n);
    fflush(stderr);
    int r = LLVMFuzzerTestOneInput(buf, got);
    fprintf(stderr, "decode returned %d\n", r);
    free(buf);
    return 0;
}
