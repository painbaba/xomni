// Known-good libyuv I420 fuzzer harness — copy and adapt.
// Targets the classic libyuv bug class: OOB read/write from stride/dimension
// inconsistencies (CVE-2017-13189 family), odd dimensions, scale paths.
//
// Input layout: 8-byte header (width, height as LE uint32) followed by I420
// planes. All src planes read from the fuzz input; over-reads hit the ASAN
// redzone. All dst buffers malloc'd to EXACTLY the size libyuv is told via
// the strides passed, so any over-write trips ASAN as a genuine library bug.
//
// IMPORTANT: keep plane allocation consistent with the strides you pass.
// Passing chroma stride = full width against a minimal 1.5*w*h layout
// guarantees an OOB read on every input (harness artifact, kills the fuzz).
// The padded layout below exercises that surface without false positives.
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "libyuv.h"
using namespace libyuv;  // libyuv wraps its whole API in namespace libyuv

static inline uint32_t rd32(const uint8_t* p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
         ((uint32_t)p[3] << 24);
}

static void scale_and_free(const uint8_t* y, int sw, int sh, const uint8_t* u,
                           int suw, const uint8_t* v, int svw, int dw, int dh,
                           enum FilterMode f) {
  int duw = (dw + 1) / 2;
  int duh = (dh + 1) / 2;
  uint8_t* dy = (uint8_t*)malloc((size_t)dw * dh);
  uint8_t* du = (uint8_t*)malloc((size_t)duw * duh);
  uint8_t* dv = (uint8_t*)malloc((size_t)duw * duh);
  if (!dy || !du || !dv) {
    free(dy);
    free(du);
    free(dv);
    return;
  }
  I420Scale(y, sw, u, suw, v, svw, sw, sh, dy, dw, du, duw, dv, duw, dw, dh, f);
  free(dy);
  free(du);
  free(dv);
}

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  if (size < 8) return 0;

  // Width/height from header bytes, clamped to 2..256 (modulo keeps
  // distribution interesting; a plain clamp makes everything 256).
  int width = (int)(rd32(data) % 255) + 2;
  int height = (int)(rd32(data + 4) % 255) + 2;

  int uw = (width + 1) / 2;   // libyuv chroma dims = ceil halves
  int uh = (height + 1) / 2;

  // Minimal layout: Y = w*h, U = uw*uh, V = uw*uh.
  size_t y_off = 8;
  size_t u_off = y_off + (size_t)width * height;
  size_t v_off = u_off + (size_t)uw * uh;
  size_t min_need = v_off + (size_t)uw * uh;
  if (size < min_need) return 0;

  const uint8_t* y = data + y_off;
  const uint8_t* u = data + u_off;
  const uint8_t* v = data + v_off;

  // Call 1: I420ToARGB, standard strides, exact dst (w*4*h).
  size_t argb_size = (size_t)width * 4 * height;
  uint8_t* argb = (uint8_t*)malloc(argb_size);
  if (!argb) return 0;
  I420ToARGB(y, width, u, uw, v, uw, argb, width * 4, width, height);

  // Call 2: ARGBToI420 back into exact-size planes.
  uint8_t* y2 = (uint8_t*)malloc((size_t)width * height);
  uint8_t* u2 = (uint8_t*)malloc((size_t)uw * uh);
  uint8_t* v2 = (uint8_t*)malloc((size_t)uw * uh);
  if (y2 && u2 && v2) {
    ARGBToI420(argb, width * 4, y2, width, u2, uw, v2, uw, width, height);
  }
  free(y2);
  free(u2);
  free(v2);

  // Call 3: I420Scale, several scale factors x filter modes.
  int f = (int)(data[8] % 4);  // kFilterNone..kFilterBox
  int dw = (width + 1) / 2, dh = (height + 1) / 2;
  if (dw >= 2 && dh >= 2)
    scale_and_free(y, width, height, u, uw, v, uw, dw, dh, (enum FilterMode)f);
  scale_and_free(y, width, height, u, uw, v, uw, width * 2, height * 2,
                 (enum FilterMode)f);
  scale_and_free(y, width, height, u, uw, v, uw, width + width / 2,
                 height + height / 2, (enum FilterMode)f);
  int dw3 = (width + 2) / 3, dh3 = (height + 2) / 3;
  if (dw3 >= 2 && dh3 >= 2)
    scale_and_free(y, width, height, u, uw, v, uw, dw3, dh3,
                   (enum FilterMode)f);

  // Call 4 (stride-mismatch surface): chroma stride = full width, using a
  // PADDED chroma layout (planes sized w*uh) so allocation stays consistent
  // with the strides — any ASAN hit here is a real library bug.
  size_t pu_off = y_off + (size_t)width * height;
  size_t pv_off = pu_off + (size_t)width * uh;
  size_t padded_need = pv_off + (size_t)width * uh;
  if (size >= padded_need) {
    const uint8_t* pu = data + pu_off;
    const uint8_t* pv = data + pv_off;
    I420ToARGB(y, width, pu, width, pv, width, argb, width * 4, width, height);
    int dw2 = (width + 1) / 2, dh2 = (height + 1) / 2;
    if (dw2 >= 2 && dh2 >= 2)
      scale_and_free(y, width, height, pu, width, pv, width, dw2, dh2,
                     (enum FilterMode)((f + 1) % 4));
  }

  free(argb);
  return 0;
}
