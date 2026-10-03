"""Fix line 217 in mps.py: change strip chars to use a variable."""
import pathlib, ast

p = pathlib.Path(r"d:\Prasoon Work\Codes\Vibe coding\Prototype\backend\nirbhar\io\mps.py")
raw_bytes = p.read_bytes()

# The bad bytes on line 217: strip("'"") -- 22 27 22 22
# We want: strip("'\"") which is: 22 27 5c 22 22
# Or simpler: define QUOTES = chr(39)+chr(34) at top and call strip(QUOTES)

# Strategy: replace the bad call with strip(chr(39)+chr(34))
bad = b'strip(\"\'" b"\")"
good = b'strip(chr(39)+chr(34))'

print("Bad bytes:", bad.hex())
print("In file:", bad in raw_bytes)

fixed_bytes = raw_bytes.replace(bad, good)
print("Changed:", fixed_bytes != raw_bytes)

new_text = fixed_bytes.decode("utf-8", errors="replace")
try:
    ast.parse(new_text)
    print("Syntax OK")
    p.write_bytes(fixed_bytes)
    print("Written")
except SyntaxError as e:
    print(f"Still broken line {e.lineno}: {e.msg}")
    lines = new_text.splitlines()
    for i in range(max(0,e.lineno-3), min(len(lines), e.lineno+2)):
        print(f"  {i+1}: {repr(lines[i])}")
