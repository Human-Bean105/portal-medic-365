import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _medi import make_handler  # noqa: E402

handler = make_handler("summary")
