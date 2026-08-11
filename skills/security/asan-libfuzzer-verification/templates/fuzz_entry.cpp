// fuzz_entry.cpp — libFuzzer harness for in-memory parsing libraries.
// Adapt: replace DGifOpen/DGifSlurp/DGifCloseFile with the target library's
// open-with-callback / parse / close sequence. Uses the library's user-data hook
// to carry the MemReader. No disk I/O in the hot path.
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdlib>
#include "gif_lib.h"  // target library header

struct MemReader {
    const uint8_t *data;
    size_t size;
    size_t pos;
};

static int mem_read(GifFileType *gif, GifByteType *buf, int n) {
    MemReader *r = (MemReader *)gif->UserData;
    if (!r || r->pos >= r->size) return 0;
    int avail = (int)(r->size - r->pos);
    if (avail > n) avail = n;
    memcpy(buf, r->data + r->pos, (size_t)avail);
    r->pos += (size_t)avail;
    return avail;
}

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    MemReader r{data, size, 0};
    int err = 0;
    GifFileType *gif = DGifOpen(&r, mem_read, &err);
    if (!gif) return 0;
    (void)DGifSlurp(gif);
    (void)DGifCloseFile(gif, &err);
    return 0;
}
