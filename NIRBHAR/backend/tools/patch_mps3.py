import pathlib, ast, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ── Fix BOUNDS in mps.py ─────────────────────────────────────────────────────
p = pathlib.Path(r"d:\Prasoon Work\Codes\Vibe coding\Prototype\backend\nirbhar\io\mps.py")
text = p.read_text(encoding="utf-8")

# Replace the BOUNDS column resolution logic with fixed-format-aware version
OLD = """        if section == "BOUNDS":
            if len(parts) < 2:
                continue
            btype = parts[0].upper()
            # Resolve column name: parts[1] or parts[2] depending on bound-set name
            cn = ""
            vs = None
            if len(parts) >= 2 and parts[1] in b.col_idx:
                cn = parts[1]
                vs = parts[2] if len(parts) > 2 else None
            elif len(parts) >= 3 and parts[2] in b.col_idx:
                cn = parts[2]
                vs = parts[3] if len(parts) > 3 else None
            elif len(parts) >= 3:
                cn = parts[2]
                vs = parts[3] if len(parts) > 3 else None
            elif len(parts) >= 2:
                cn = parts[1]
                vs = parts[2] if len(parts) > 2 else None
            if not cn:
                continue
            if cn not in b.col_idx:
                raise ParseError(lineno, src, f"BOUNDS: unknown column {cn!r}")"""

NEW = """        if section == "BOUNDS":
            if len(parts) < 2:
                continue
            btype = parts[0].upper()
            # Resolve column name using free-format first, fixed-format fallback
            # Fixed-format BOUNDS: btype 1-2, bnd_name 4-12, col_name 14-22, value 24-36
            cn = ""
            vs = None
            # Free-format: try parts[1] then parts[2] as column name
            if len(parts) >= 2 and parts[1] in b.col_idx:
                cn = parts[1]
                vs = parts[2] if len(parts) > 2 else None
            elif len(parts) >= 3 and parts[2] in b.col_idx:
                cn = parts[2]
                vs = parts[3] if len(parts) > 3 else None
            else:
                # Fixed-format fallback: col_name at positions 14-22, value at 24-36
                ff_cn = _ff(raw_line, 14, 22)
                ff_vs = _ff(raw_line, 24, 36)
                if ff_cn and ff_cn in b.col_idx:
                    cn = ff_cn
                    vs = ff_vs if ff_vs else None
                elif len(parts) >= 3:
                    cn = parts[2]
                    vs = parts[3] if len(parts) > 3 else None
                elif len(parts) >= 2:
                    cn = parts[1]
                    vs = parts[2] if len(parts) > 2 else None
            if not cn:
                continue
            if cn not in b.col_idx:
                raise ParseError(lineno, src, f"BOUNDS: unknown column {cn!r}")"""

text2 = text.replace(OLD, NEW)
print("BOUNDS fix:", text2 != text)
text = text2

p.write_text(text, encoding="utf-8")
ast.parse(text)
print("mps.py syntax OK")
