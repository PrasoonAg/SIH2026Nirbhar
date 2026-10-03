import pathlib, ast, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

p = pathlib.Path(r"d:\Prasoon Work\Codes\Vibe coding\Prototype\backend\nirbhar\linalg\lu_markowitz.py")
text = p.read_text(encoding="utf-8")

# Replace the factor() method to always use pure NumPy (no lu_factor/lu_solve)
OLD = """        # NumPy LU: uses LAPACK dgetrf
        try:
            lu, piv = np.linalg.lu_factor(B)  # type: ignore[attr-defined]
        except AttributeError:
            # numpy < 2.0 compat fallback using scipy-free approach
            lu, piv = _lu_factor_pure(B)"""
NEW = """        # Pure NumPy LU (scipy-free, works on all numpy versions)
        lu, piv = _lu_factor_pure(B)"""
text2 = text.replace(OLD, NEW)
print("Fix factor:", text2 != text)
text = text2

# Replace the solve() method to always use pure NumPy
OLD2 = """        try:
            return np.linalg.lu_solve(  # type: ignore[attr-defined]
                (self.lu, self.piv), rhs, trans=1 if transpose else 0
            )
        except AttributeError:
            return _lu_solve_pure(self.lu, self.piv, rhs, transpose)"""
NEW2 = """        return _lu_solve_pure(self.lu, self.piv, rhs, transpose)"""
text2 = text.replace(OLD2, NEW2)
print("Fix solve:", text2 != text)
text = text2

p.write_text(text, encoding="utf-8")
ast.parse(text)
print("lu_markowitz.py syntax OK")
