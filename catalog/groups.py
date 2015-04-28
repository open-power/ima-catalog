from struct import *
import csv
from common import *

def group_pack(group):
    header = pack(">xxIBxHHBB", group['flag'], group['domain'], \
                  group['event group offset'], group['event group length'], \
                  group['schema index'], group['event count'])

    indexes = pack(">16H", *eval(group['event indexes']))

    g = header + indexes + pack_text(group['name']) + pack_text(group['description'])
    return pad16(g)

def pack_groups(groups_csv):
    groups = ""

    with open(groups_csv) as csvfile:
        reader = csv.DictReader(csvfile)
        group = {}
        count = 0
        for row in reader:
            count += 1
            group['flag'] = int(row['flag'])
            group['domain'] = int(row['domain'])
            group['event group offset'] = int(row['event group offset'])
            group['event group length'] = int(row['event group length'])
            group['schema index'] = int(row['schema index'])
            group['event count'] = int(row['event count'])
            group['event indexes'] = row['event indexes']
            group['name'] = row['name']
            group['description'] = row['description']

            groups += group_pack(group)

        return pad_page(groups, PAGE_SIZE), count

if __name__ == "__main__":
    groups = pack_groups('groups.csv')
    if len(groups) == 0:
        print "Error in generating groups binary dump"

    f = open('groups.bin', 'w')
    f.write(groups)
    f.close()
    hexdump(groups, " ", 16)
