import pathlib, ast
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

p = pathlib.Path(r"d:\Prasoon Work\Codes\Vibe coding\Prototype\backend\nirbhar\io\mps.py")
text = p.read_text(encoding="utf-8")

# Fix 1: Section headers must NOT start with a space
OLD1 = "        if first in _SECTIONS:\n            section = first\n            if section == \"ENDATA\":\n                break\n            continue"
NEW1 = "        if first in _SECTIONS and not line.startswith(\" \"):\n            section = first\n            if section == \"ENDATA\":\n                break\n            continue"
text2 = text.replace(OLD1, NEW1)
print("Fix1:", text2 != text)
text = text2

# Fix 2+3: RHS/RANGES - handle no-prefix format (row name as first token)
for sec, err in [("RHS","RHS"), ("RANGES","RANGES")]:
    needle_start = f"                idx = 1\n                while idx + 1 < len(parts):\n                    rn2, vs = parts[idx], parts[idx + 1]\n                    idx += 2\n                    val = _flt(vs, lineno, src)\n                    if rn2 not in b.row_idx:\n                        raise ParseError(lineno, src, f\"{err}: unknown row {{rn2!r}}\")\n                    b.rhs[b.row_idx[rn2]] = val" if sec == "RHS" else f"                idx = 1\n                while idx + 1 < len(parts):\n                    rn2, vs = parts[idx], parts[idx + 1]\n                    idx += 2\n                    val = _flt(vs, lineno, src)\n                    if rn2 not in b.row_idx:\n                        raise ParseError(lineno, src, f\"{err}: unknown row {{rn2!r}}\")\n                    b.rng[b.row_idx[rn2]] = val"
    store = "b.rhs[b.row_idx[rn2]] = val" if sec == "RHS" else "b.rng[b.row_idx[rn2]] = val"
    repl = f"                start = 0 if parts[0] in b.row_idx else 1\n                idx = start\n                while idx + 1 < len(parts):\n                    rn2, vs = parts[idx], parts[idx + 1]\n                    idx += 2\n                    val = _flt(vs, lineno, src)\n                    if rn2 not in b.row_idx:\n                        raise ParseError(lineno, src, f\"{err}: unknown row {{rn2!r}}\")\n                    {store}"
    text2 = text.replace(needle_start, repl)
    print(f"Fix {sec}:", text2 != text)
    text = text2

# Fix 4: COLUMNS - when free-format but parts[1] not in row_idx -> use fixed-format
OLD4 = "            if is_free:\n                j = b.col(parts[0])"
NEW4 = "            if is_free and (len(parts) < 2 or parts[1] in b.row_idx):\n                j = b.col(parts[0])"
text2 = text.replace(OLD4, NEW4)
print("Fix4:", text2 != text)
text = text2

p.write_text(text, encoding="utf-8")
try:
    ast.parse(text)
    print("mps.py syntax OK")
except SyntaxError as e:
    print(f"mps.py broken line {e.lineno}: {e.msg}")
    ls = text.splitlines()
    for j in range(max(0,e.lineno-2), min(len(ls),e.lineno+2)):
        print(f"  {j+1}: {repr(ls[j])}")

# Fix check_imports.py - replace unicode emoji with ASCII
ci_p = pathlib.Path(r"d:\Prasoon Work\Codes\Vibe coding\Prototype\backend\tools\check_imports.py")
ci_text = ci_p.read_text(encoding="utf-8")
ci_fixed = ci_text
for bad, good in [(chr(0x2705), "[PASS]"), (chr(0x274c), "[FAIL]"), (chr(0x2713), "[OK]"), (chr(0x2717), "[X]")]:
    ci_fixed = ci_fixed.replace(bad, good)
if ci_fixed != ci_text:
    ci_p.write_text(ci_fixed, encoding="utf-8")
    print("Fixed check_imports.py emoji")
else:
    print("check_imports.py no emoji found")
