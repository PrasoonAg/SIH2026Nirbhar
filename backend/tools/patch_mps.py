import pathlib, ast

p = pathlib.Path(r"d:\Prasoon Work\Codes\Vibe coding\Prototype\backend\nirbhar\io\mps.py")
raw = p.read_bytes()

# The bad bytes we see: strip("'""): 73 74 72 69 70 28 22 27 22 22 29
# Lets find them:
bad_seq = bytes([0x73,0x74,0x72,0x69,0x70,0x28,0x22,0x27,0x22,0x22,0x29])  # strip("'"")
good_seq = b'strip(chr(39)+chr(34))'
print("Bad seq:", bad_seq)
print("Found:", bad_seq in raw)
print("Count:", raw.count(bad_seq))

fixed = raw.replace(bad_seq, good_seq)
print("Fixed count:", fixed.count(bad_seq))

new_text = fixed.decode("utf-8")
try:
    ast.parse(new_text)
    print("Syntax OK")
    p.write_bytes(fixed)
    print("Saved")
except SyntaxError as e:
    print("Still broken:", e.lineno, e.msg)
    ls = new_text.splitlines()
    for j in range(max(0,e.lineno-2), min(len(ls), e.lineno+3)):
        print(f"  {j+1}: {repr(ls[j])}")
