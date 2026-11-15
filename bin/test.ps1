# Usage: .\bin\test.ps1
.\.venv\Scripts\activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
