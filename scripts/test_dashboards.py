"""Exercise actual Streamlit scripts in each standalone Docker image."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    settings = {
        'cloudguard': (1, '5M', ['Previsioni e allarmi', 'Risultati']),
        'stocksense': (1, '5M', ['Da fare oggi', 'Prodotto', 'Risultati']),
        'solarcast': (0, '5M', ['Demo retrospettiva', 'Risultati']),
    }
    for project, (selector, model, pages) in settings.items():
        code = "from streamlit.testing.v1 import AppTest\n"
        code += "a=AppTest.from_file('/app/app/streamlit_app.py').run(timeout=120)\n"
        code += "assert not a.exception, a.exception\n"
        if args.models:
            code += f"a.sidebar.selectbox[{selector}].set_value('{model}').run(timeout=120)\n"
            code += "assert not a.exception, a.exception\n"
            code += "assert not a.error, a.error\n"
            if project == 'solarcast':
                code += "a.sidebar.selectbox[1].set_value('B').run(timeout=120)\n"
                code += "assert not a.exception and not a.error\n"
        for page in pages:
            code += f"a.sidebar.radio[0].set_value({page!r}).run(timeout=120)\n"
            code += "assert not a.exception and not a.error\n"
        code += f"print('{project}: dashboard PASS')\n"
        subprocess.run(['docker', 'compose', 'run', '--rm', '--no-deps', project,
                        'python', '-c', code], cwd=root, check=True)


if __name__ == '__main__':
    main()
