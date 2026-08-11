# Observed MSYS/Windows path failures (for recognition)

All captured 2026-08-07 on this host while wiring the z.ai key and the
glm CLI bash wrapper.

## 1. python3 argv with MSYS path (silent key-append failure)
Command shape: `python3 -c "...open(kp)..." "/c/Users/HP/AppData/Local/Temp/zai_key.txt" ...`
```
Traceback (most recent call last):
  File "<string>", line 4, in <module>
    key = open(kp).read().strip()
FileNotFoundError: [Errno 2] No such file or directory: '/c/Users/HP/AppData/Local/Temp/zai_key.txt'
```
Meanwhile, in the SAME shell: `K=$(cat "$TMP")` worked (bash resolves the
MSYS path) and `rm "$TMP"` worked. Python could not.
FIX: pass `C:/Users/HP/AppData/Local/Temp/zai_key.txt` (forward slashes
OK for Windows python).

## 2. node --check false positives from the auto-lint
Every patch/write_file edit to a .js file under C:\Users\HP\... reports:
```
node:internal/modules/cjs/loader:1503
  throw err;
Error: Cannot find module 'C:\c\Users\HP\glm-tool\glm_puter.js'
    at node:internal/modules/cjs/loader:1500:15
    at node:internal/main/check_syntax:33:20
```
Note the doubled `C:\c\Users\...` — the lint wrapper prepends the drive
to the MSYS path. This is NOT a syntax error. Real check:
`cd /c/Users/HP/glm-tool && node --check glm_puter.js` → passes.

## 3. bash wrapper invoking Windows binaries with $DIR (MSYS)
```
python3 "$DIR/glm_nim.py"   # DIR=/c/Users/HP/glm-tool
C:\Users\HP\AppData\Local\Microsoft\WindowsApps\python3.exe: can't open file
'C:\\c\\Users\\HP\\glm-tool\\glm_nim.py': [Errno 2] No such file or directory
```
FIX (in the wrapper):
```
WINDIR="$(cygpath -w "$DIR" 2>/dev/null || echo "$DIR")"
python3 "$WINDIR/glm_nim.py"
```

## 4. Related: native curl /tmp mismatch
`curl -o /tmp/ghcat.json` succeeded (exit 0) but `head /tmp/ghcat.json`
→ "No such file or directory" (native Windows curl wrote elsewhere).
Write curl outputs to `~/...` or C:/Users/HP paths.
