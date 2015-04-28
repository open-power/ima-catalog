from struct import *
import csv
from common import *

NAMELEN_OFFSET = 0x10

def read_formula(formula_dump):
    formula = {}
    tlen, formula['flag'], formula['group'] = unpack_from(">HxxIH6x",
                                                          formula_dump)

    formula['name'], nlen = read_string(formula_dump[NAMELEN_OFFSET:])
    formula['description'], dlen = read_string(formula_dump[(NAMELEN_OFFSET + nlen):])
    formula['formula'], flen = read_string(formula_dump[(NAMELEN_OFFSET + nlen + dlen):])

    print formula['name']

    return tlen, formula

def read_formulae():
    f = open('81e00610.v7.lid', 'r')
    f.seek(0x2d000, 0)
    formula_length = 0x2
    dump = f.read(PAGE_SIZE * formula_length)

    i = 0
    formula_count = 0x24
    offset = 0
    f = open('formula.csv', 'wt')
    try:
        writer = csv.writer(f)

        for i in range(0, formula_count):
            flen, formula = read_formula(dump[offset:])
            offset += flen
            if i == 0:
                writer.writerow((formula.keys()))
            writer.writerow((formula.values()))
    finally:
        f.close()

read_formulae()
