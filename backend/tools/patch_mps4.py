import pathlib, ast, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

p = pathlib.Path(r"d:\Prasoon Work\Codes\Vibe coding\Prototype\backend\nirbhar\io\mps.py")
text = p.read_text(encoding="utf-8")

# Fix ROWS section: use fixed-format for rows with space-containing names
# MPS ROWS format: " E  DEDO3 1R" -> type at [1], name at [4:12]
# Free-format: parts[0]=type, parts[1]=name (works if name has no spaces)
# Fixed-format: type at raw_line[1], name at raw_line[4:12]

OLD = """        if section == "ROWS":
            if len(parts) < 2:
                raise ParseError(lineno, src, f"ROWS: {line!r}")
            rt, rn = parts[0].upper(), parts[1]
            if rt not in ("N", "E", "G", "L"):
                raise ParseError(lineno, src, f"ROWS: unknown type {rt!r}")
            b.row(rn, rt)
            if rt == "N" and not b.obj_name:
                b.obj_name = rn
            continue"""

NEW = """        if section == "ROWS":
            if len(parts) < 2:
                raise ParseError(lineno, src, f"ROWS: {line!r}")
            rt = parts[0].upper()
            if rt not in ("N", "E", "G", "L"):
                raise ParseError(lineno, src, f"ROWS: unknown type {rt!r}")
            # Fixed-format: row name at positions 4-12 (handles space-containing names)
            # Free-format: row name is parts[1]
            # Use fixed-format if the line has the standard MPS 1-char indent + space + type
            if len(raw_line) > 4 and raw_line[0] == " ":
                rn = _ff(raw_line, 4, 12)
                if not rn:
                    rn = parts[1]  # fallback
            else:
                rn = parts[1]
            b.row(rn, rt)
            if rt == "N" and not b.obj_name:
                b.obj_name = rn
            continue"""

text2 = text.replace(OLD, NEW)
print("ROWS fix:", text2 != text)
text = text2

# Also fix COLUMNS: the check parts[1] in b.row_idx can now correctly discriminate
# because row names like "DEDO3 1R" are registered correctly
# The is_free check: parts[2] is float AND parts[1] in row_idx -> free-format
# For forplan: parts=['DEDO3', '11', 'AZ', '20', '1.'] where 'DEDO3' is NOT a row
# (row is 'DEDO3 1R') so is_free stays False -> fixed-format. Correct!

p.write_text(text, encoding="utf-8")
ast.parse(text)
print("mps.py syntax OK")
