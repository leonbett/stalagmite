import os
import pandas as pd

import config

from subject import Subject

from gen_tex_accuracy_table import generate_precision_recall_latex_table


def main():
    subjects = [
        Subject('tinyc', 'http://www.iro.umontreal.ca/~felipe/IFT2030-Automne2002/Complements/tinyc.c'),
        Subject('lisp', 'https://github.com/mystor/simple-lisp-parser-in-c/blob/master/parse.c'),
        Subject('json', 'https://github.com/vrthra/mimid/blob/master/Cmimid/examples/json.c'),
        Subject('calc', 'https://github.com/fbuihuu/parser/blob/master/rdp.c'),
    ]

    generate_precision_recall_latex_table(subjects)


if __name__ == "__main__":
    main()
