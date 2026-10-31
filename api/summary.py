import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from medi.web import make_handler  # noqa: E402


class handler(make_handler("summary")):
    pass
