#!/bin/zsh
cd -- "${0:A:h}"
if [[ -x .venv/bin/python ]]; then
  .venv/bin/python app.py
elif [[ -x /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 ]]; then
  /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py
else
  python3 app.py
fi
