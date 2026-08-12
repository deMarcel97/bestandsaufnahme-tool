import shutil
from pathlib import Path

src = Path("data/auf-testeii")
dst = Path("data/auf-test")

if src.exists():
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    auftrag_yaml = dst / "auftrag.yaml"
    content = auftrag_yaml.read_text()
    content = content.replace("id: auf-testeii", "id: auf-test")
    auftrag_yaml.write_text(content)
    print("Successfully created data/auf-test from data/auf-testeii")
