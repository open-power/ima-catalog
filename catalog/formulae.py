# Pack the formulae into a binary dump to be used in the catalog
from struct import *
import csv
from common import *


def formula_pack(formula):
    # First pack the header
    header = pack(">xxIH6x", formula['flag'], formula['group'])

    st = header + pack_text(formula['name']) + pack_text(formula['desc']) + pack_text(formula['formula']) + pack_text(formula['unit'])
    t = pad16(st)               # this also adds the length

    return t


def pack_formulae(formulae_csv):
    formulae = ""

    with open(formulae_csv) as csvfile:
        reader = csv.DictReader(csvfile)
        formula = {}
        count = 0
        for row in reader:
            count += 1
            formula['name'] = row['Formula Name']
            formula['desc'] = row['Formula Description']
            formula['formula'] = row['Formula']
            formula['unit'] = row['Unit']
            formula['group'] = int(row['Group'])

            if row['Grouped'] == 'y':
                formula['flag'] = 0x04
            else:
                formula['flag'] = 0

            formulae += formula_pack(formula)

        return pad_page(formulae, PAGE_SIZE), count


if __name__ == "__main__":
    formulae = pack_formulae('formulae.csv')
    if len(formulae) == 0:
        print "Error in generating formulae binary dump"

    f = open('formulae.bin', 'w')
    f.write(formulae)
    f.close()
    hexdump(formulae, " ", 16)
