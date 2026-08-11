# Windows: llama.cpp GPU showing 0 MiB / --list-devices (none)

Verified 2026-08-06, Windows 10, RTX 3050 Laptop, driver 592.82
(CUDA 13.1), llama.cpp b10293 win-cuda build.

## Symptom

- `llama-server.exe --n-gpu-layers 99` runs fine but `nvidia-smi`
  shows `0 MiB` GPU memory used — model runs on CPU (~4-14 tok/s
  for 1.5B Q4 instead of 60-100+).
- `llama-server.exe --list-devices` prints `Available devices: (none)`.
- Startup log has NO `CUDA0: ...` line and NO error.

## Root cause

The prebuilt `llama-bXXXX-bin-win-cuda-12.4/13.3-x64.zip` from GitHub
releases contains `ggml-cuda.dll` but NOT the CUDA runtime math
libraries. `ggml-cuda.dll` imports `cublas64_13.dll` +
`cublasLt64_13.dll` at load time. Without them the CUDA backend
silently fails and llama.cpp falls back to CPU. No error is printed —
that's what makes it confusing. Also: build CUDA version must be
compatible with the driver (CUDA 13.3 build worked on the 13.1 driver;
the 12.4 build did not engage).

## Fix (verified)

1. Find which cuBLAS version the build needs — scan the DLL:
   ```bash
   python -c "
   import re
   data = open('llama_cpp_bin/ggml-cuda.dll','rb').read()
   print(sorted({d.decode() for d in re.findall(rb'[A-Za-z0-9_\-]+\.dll', data) if b'cublas' in d.lower()}))"
   ```
   → `['cublas64_13.dll', 'cublasLt64_13.dll']` for CUDA 13.3 build.

2. Download the matching cuBLAS redist (NOT API-rate-limited, unlike
   api.github.com):
   ```
   https://developer.download.nvidia.com/compute/cuda/redist/libcublas/windows-x86_64/
   ```
   Pick `libcublas-windows-x86_64-13.3.0.5-archive.zip` (match major.minor).

3. Extract and copy both DLLs next to llama-server.exe:
   ```bash
   unzip libcublas-windows-x86_64-13.3.0.5-archive.zip
   cp libcublas-*/bin/x64/cublas64_13.dll  llama_cpp_bin/
   cp libcublas-*/bin/x64/cublasLt64_13.dll llama_cpp_bin/
   ```

4. VERIFY BEFORE starting the server:
   ```bash
   cd llama_cpp_bin && ./llama-server.exe --list-devices
   # expect: CUDA0: NVIDIA GeForce RTX 3050 Laptop GPU (4095 MiB, ...)
   ```

5. Start server, then confirm GPU is claimed:
   ```bash
   nvidia-smi --query-gpu=memory.used --format=csv   # expect >0 MiB
   ```

## Pitfalls

- `--list-devices` returning `(none)` is the definitive pre-flight
  check. Never trust `--n-gpu-layers 99` alone.
- Symptom-first diagnosis: GPU at 0 MiB + slow tok/s = missing CUDA
  runtime DLLs, not a broken GPU, not a driver problem.
- Match CUDA major versions: 13.3 build needs 13.x cuBLAS; 12.4 build
  needs 12.x cuBLAS. Driver 592.82 (CUDA 13.1) worked with 13.3 build.
- The NVIDIA redist index is plain HTML directory listing — scrape
  `href=` entries; GitHub API rate limit does not apply there.
