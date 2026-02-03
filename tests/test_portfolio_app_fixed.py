import ast
from pathlib import Path


def _load_function_from_file(path: Path, func_name: str):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    func_node = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            func_node = node
            break
    if func_node is None:
        raise AssertionError(f"Function {func_name!r} not found in {path}")

    module = ast.Module(body=[func_node], type_ignores=[])
    compiled = compile(module, filename=str(path), mode="exec")
    ns = {}
    exec(compiled, ns)
    return ns[func_name]


def test_sum_two_integers_adds():
    func = _load_function_from_file(
        Path(__file__).resolve().parents[1] / "portfolio_app_fixed.py",
        "sum_two_integers",
    )
    assert func(2, 3) == 5
    assert func(-1, 1) == 0
