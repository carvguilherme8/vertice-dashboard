import sys
from pathlib import Path

SOLUCAO_FINAL_DIR = Path(__file__).resolve().parents[1] / "solucao_final"
if str(SOLUCAO_FINAL_DIR) not in sys.path:
    sys.path.insert(0, str(SOLUCAO_FINAL_DIR))
