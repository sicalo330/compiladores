from utils import build_tree
from rich import print
from parser import parse 


def main():
    with open("test/good3.bminor", "r") as f:
        code = f.read()
        parse(code)
        