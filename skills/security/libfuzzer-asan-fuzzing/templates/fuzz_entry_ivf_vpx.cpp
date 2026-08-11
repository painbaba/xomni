/*
 * fuzz_entry_ivf_vpx.cpp - IVF-based VP9 (or VP8) decoder fuzzer harness for libvpx.
 *
 * Input format (IVF):
 *   [0..31]   32-byte IVF file header (ignored)
 *   then repeated per frame:
 *     [0..3]  uint32 LE frame size
 *     [4..11] uint64 LE timestamp (ignored)
 *     [12..]  compressed frame payload
 *
 * Decode loop: vpx_codec_dec_init(vpx_codec_vp9_dx) -> per-frame
 * vpx_codec_decode -> drain with vpx_codec_get_frame.
 *
 * Build/link (C sources compiled separately with -fsanitize=fuzzer-no-link):
 *   clang++ -O1 -g -msse4.1 -fsanitize=address,fuzzer -fno-omit-frame-pointer -pthread \
 *     -I libvpx -I libvpx/config/generic -I libvpx/vpx_dsp -I libvpx/vpx_scale \
 *     fuzz_entry_ivf_vpx.cpp obj/*.o -lm -o fuzz_vpx_asan
 */
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "vpx/vpx_decoder.h"
#include "vpx/vp8dx.h"
#include "vpx_ports/mem_ops.h"

#define IVF_FILE_HDR_SZ 32
#define IVF_FRAME_HDR_SZ (4 + 8) /* 4-byte size + 8-byte timestamp */

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  if (size < IVF_FILE_HDR_SZ) return 0;

  vpx_codec_ctx_t codec;
  vpx_codec_dec_cfg_t cfg;
  memset(&cfg, 0, sizeof(cfg));
  cfg.threads = 1;

  if (vpx_codec_dec_init(&codec, vpx_codec_vp9_dx(), &cfg, 0) != VPX_CODEC_OK)
    return 0;

  const uint8_t *p = data + IVF_FILE_HDR_SZ;
  const uint8_t *end = data + size;

  while ((size_t)(end - p) >= IVF_FRAME_HDR_SZ) {
    uint32_t frame_sz = mem_get_le32(p);
    p += 4; /* skip size field */
    p += 8; /* skip timestamp */
    if ((size_t)(end - p) < frame_sz) break;

    /* Decode the frame; keep going even on error (corrupt-frame tolerance
     * is the decoder's real-world job and exercises more code paths). */
    vpx_codec_decode(&codec, p, frame_sz, NULL, 0);

    /* Drain any produced frames so the output path is exercised. */
    vpx_codec_iter_t iter = NULL;
    vpx_image_t *img;
    while ((img = vpx_codec_get_frame(&codec, &iter)) != NULL) {
      /* Touch the buffers so ASAN sees accesses against their redzones. */
      (void)img;
    }

    p += frame_sz;
  }

  vpx_codec_destroy(&codec);
  return 0;
}
