"""Check whether the radar project Python environment is ready."""

from __future__ import annotations

import importlib.util


REQUIRED_PACKAGES = [
    ("matplotlib", "matplotlib"),
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("pyserial", "serial"),
    ("scikit-learn", "sklearn"),
    ("scipy", "scipy"),
]


def main() -> None:
    missing = []
    for package_name, import_name in REQUIRED_PACKAGES:
        available = importlib.util.find_spec(import_name) is not None
        status = "OK" if available else "MISSING"
        print(f"{package_name:14s} {status}")
        if not available:
            missing.append(package_name)

    if missing:
        print()
        print("Install missing packages with:")
        print("python -m pip install -r requirements.txt")
        raise SystemExit(1)

    print()
    print("Environment ready.")


if __name__ == "__main__":
    main()
