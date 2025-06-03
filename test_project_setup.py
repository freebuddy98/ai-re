import os
import toml

PROJECT_DIR = "eventbus"
UTILS_FILE = os.path.join(PROJECT_DIR, "utils.py")
PYPROJECT_FILE = "pyproject.toml"


def test_project_structure():
    assert os.path.isdir(PROJECT_DIR), f"目录 {PROJECT_DIR} 不存在"
    assert os.path.isfile(UTILS_FILE), f"文件 {UTILS_FILE} 不存在"
    assert os.path.isfile(PYPROJECT_FILE), f"文件 {PYPROJECT_FILE} 不存在"

def test_pyproject_toml_has_ruff():
    assert os.path.isfile(PYPROJECT_FILE), f"文件 {PYPROJECT_FILE} 不存在"
    data = toml.load(PYPROJECT_FILE)
    deps = data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {})
    assert "ruff" in deps, "pyproject.toml 未声明 ruff 依赖" 