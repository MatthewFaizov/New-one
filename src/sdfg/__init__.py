def main() -> None:
    """Запуск командой: uv run sdfg"""
    import os
    import sys

    # Чтобы app.py нашёл соседние файлы database.py и ai.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import app

    app.run(debug=True)
