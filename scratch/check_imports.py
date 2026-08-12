import ast
import os
from pathlib import Path

app_dir = Path("app")
py_files = list(app_dir.rglob("*.py")) + [Path("abnahme.py")]

for py_file in py_files:
    with open(py_file, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        tree = ast.parse(content, filename=str(py_file))
    except Exception as e:
        print(f"Syntax error in {py_file}: {e}")
        continue

    # Find used annotations and Name nodes
    defined = set(dir(__builtins__))
    imported = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.asname or alias.name)

    all_known = defined | imported

    # Check for common typing symbols used in annotations but not imported
    typing_symbols = {"List", "Dict", "Set", "Tuple", "Optional", "Any", "Union", "Callable"}
    
    missing_typing = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in typing_symbols:
            if node.id not in all_known:
                missing_typing.add(node.id)

    if missing_typing:
        print(f"{py_file}: Missing typing imports: {missing_typing}")
