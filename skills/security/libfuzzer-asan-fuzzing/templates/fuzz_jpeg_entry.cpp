/* Fuzz harness for AOSP libjpeg-turbo decoder (Android's JPEG path).
 * Custom source manager (jpeg_mem_src does NOT exist in old/AOSP trees),
 * setjmp/longjmp error exit, full decode: read_header -> start_decompress
 * -> scanlines -> finish -> destroy.
 *
 * Build (see references/jpeg-aosp-fuzzer-session.md for the full file list):
 *   clang++ -std=gnu++14 -O1 -g -fsanitize=address,fuzzer -fno-omit-frame-pointer \
 *     -I jpeg fuzz_jpeg_entry.cpp <decode-only .c list> -o fuzz_jpeg_asan
 *   -std=gnu++14: IJG C code uses 'register' (ERROR in C++17).
 *   jdphuff.c (AOSP tile code) needs a sed cast for C++: index->scan = realloc(...)
 *
 * Two hard-won rules baked in:
 * 1. skip_input_data MUST be the IJG refill LOOP. A single-fill variant underflows
 *    bytes_in_buffer (size_t) and walks next_input_byte past the static eoi[] ->
 *    ASAN global-buffer-overflow in next_marker() at jpeg_finish_decompress (harness
 *    bug, not a jpeg finding).
 * 2. Hard-reject dims > 4096. Scaling (scale_denom) only shrinks the OUTPUT buffer;
 *    entropy-decode/IDCT work stays full-resolution, so 65535x65535 header claims
 *    grind ~119M MCU blocks -> libFuzzer per-input timeout -> ABORTS the whole run.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include "jpeglib.h"

static jmp_buf jpeg_jmp;

static void jpeg_error_exit(j_common_ptr cinfo) {
    longjmp(jpeg_jmp, 1);
}

static void init_source(j_decompress_ptr cinfo) {}
static boolean fill_input_buffer(j_decompress_ptr cinfo) {
    /* EOD: insert fake EOI marker so decode terminates */
    static JOCTET eoi[2] = {0xFF, 0xD9};
    cinfo->src->next_input_byte = eoi;
    cinfo->src->bytes_in_buffer = 2;
    return TRUE;
}
static void skip_input_data(j_decompress_ptr cinfo, long num_bytes) {
    /* Standard IJG loop: re-fill until all requested bytes are consumed. */
    if (num_bytes > 0) {
        while (num_bytes > (long) cinfo->src->bytes_in_buffer) {
            num_bytes -= (long) cinfo->src->bytes_in_buffer;
            fill_input_buffer(cinfo);
        }
        cinfo->src->next_input_byte += num_bytes;
        cinfo->src->bytes_in_buffer -= (size_t) num_bytes;
    }
}
static void term_source(j_decompress_ptr cinfo) {}

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    if (size < 2) return 0;

    struct jpeg_decompress_struct cinfo;
    struct jpeg_error_mgr jerr;
    struct jpeg_source_mgr src;
    memset(&cinfo, 0, sizeof(cinfo));
    memset(&src, 0, sizeof(src));
    cinfo.err = jpeg_std_error(&jerr);
    jerr.error_exit = jpeg_error_exit;  /* longjmp instead of exit() */

    if (setjmp(jpeg_jmp)) {
        /* JPEG library error — clean bail, NOT a crash */
        jpeg_destroy_decompress(&cinfo);
        return 0;
    }
    jpeg_create_decompress(&cinfo);

    src.init_source = init_source;
    src.fill_input_buffer = fill_input_buffer;
    src.skip_input_data = skip_input_data;
    src.resync_to_restart = jpeg_resync_to_restart;
    src.term_source = term_source;
    src.bytes_in_buffer = size;
    src.next_input_byte = (JOCTET*)data;
    cinfo.src = &src;

    if (jpeg_read_header(&cinfo, TRUE) != JPEG_HEADER_OK) {
        jpeg_destroy_decompress(&cinfo);
        return 0;
    }
    if (cinfo.image_width == 0 || cinfo.image_height == 0) {
        jpeg_destroy_decompress(&cinfo);
        return 0;
    }
    /* Hard cap: keeps per-input decode work bounded (see header comment). */
    if (cinfo.image_width > 4096 || cinfo.image_height > 4096) {
        jpeg_destroy_decompress(&cinfo);
        return 0;
    }
    if (!jpeg_start_decompress(&cinfo)) {
        jpeg_destroy_decompress(&cinfo);
        return 0;
    }
    JSAMPARRAY row = (*cinfo.mem->alloc_sarray)((j_common_ptr)&cinfo, JPOOL_IMAGE,
                        (JDIMENSION)(cinfo.output_width * cinfo.output_components), 1);
    if (row) {
        while (cinfo.output_scanline < cinfo.output_height) {
            if (jpeg_read_scanlines(&cinfo, row, 1) < 1) break;
        }
    }
    jpeg_finish_decompress(&cinfo);
    jpeg_destroy_decompress(&cinfo);
    return 0;
}
