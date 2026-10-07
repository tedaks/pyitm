"""Static inventory: every '/' or '/=' site in pyitm_ng, comments and docstrings stripped."""
import ast
import pathlib

for path in sorted(pathlib.Path("pyitm_ng").glob("*.py")):
    src = path.read_text()
    lines = src.splitlines()
    tree = ast.parse(src)
    # blank out docstrings and comments: collect docstring line ranges
    drop = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                for ln in range(body[0].lineno, body[0].end_lineno + 1):
                    drop.add(ln)
    print(f"\n===== {path} =====")
    for i, line in enumerate(lines, 1):
        if i in drop or line.lstrip().startswith("#"):
            continue
        code = line.split("#")[0] if not line.lstrip().startswith("#") else ""
        if "/" in code:
            print(f"{i:4d}  {code.strip()}")
