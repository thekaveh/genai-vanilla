from pathlib import Path; print(f"__file__: {__file__}"); print(f"Resolved: {Path(__file__).resolve()}"); print(f"Parent.parent: {Path(__file__).resolve().parent.parent}")
