from struct import *
from common import *

GNAMELEN_OFFSET = 0x30
ENAMELEN_OFFSET = 0x14
FNAMELEN_OFFSET = 0x10

def read_group(group_dump):
    group = {}
    glen, group['flag'], group['domain'], group['event group offset'], \
        group['event group length'], group['schema index'], \
        group['event count'] = unpack_from(">HxxIBxHHBB", group_dump)
    group['event indexes'] = unpack_from(">16H", group_dump[0x10:])
    group['name'], nlen = read_string(group_dump[GNAMELEN_OFFSET:])
    group['description'], dlen = read_string(group_dump[(GNAMELEN_OFFSET + nlen):])

    return glen, group

def read_formula(formula_dump):
    formula = {}
    tlen, formula['flag'], formula['group'] = unpack_from(">HxxIH6x",
                                                          formula_dump)

    formula['name'], nlen = read_string(formula_dump[FNAMELEN_OFFSET:])
    formula['description'], dlen = read_string(formula_dump[(FNAMELEN_OFFSET + nlen):])
    formula['formula'], flen = read_string(formula_dump[(FNAMELEN_OFFSET + nlen + dlen):])

    return tlen, formula

def read_event(event_dump):
    event = {}
    elen, event['domain'], event['record byte offset'], event['record length'], \
        event['counter offset'], event['flag'], event['primary group index'], \
        event['group count'] = unpack_from(">HxxBxHHHIHH", event_dump)

    event['name'], nlen = read_string(event_dump[ENAMELEN_OFFSET:])
    event['description'], dlen = read_string(event_dump[(ENAMELEN_OFFSET + nlen):])
    event['detailed description'], ddlen = read_string(event_dump[(ENAMELEN_OFFSET + nlen + dlen):])

    return elen, event

def read_groups(dump_file, page_offset, num_pages, num_count, group_type):
    f = open(dump_file, 'r')
    f.seek(page_offset * PAGE_SIZE, 0)
    dump = f.read(PAGE_SIZE * num_pages)

    if group_type == 'groups':
        read_fn = read_group
    elif group_type == 'events':
        read_fn = read_event
    elif group_type == 'formulae':
        read_fn = read_formula
    else:
        print "No such group"

    offset = 0
    groups = []
    for i in range(0, num_count):
        glen, group = read_fn(dump[offset:])
        offset += glen
        groups.append(group)

    f.close()

    return groups

# write_to_csv('formulae.csv', read_groups('81e00610.v7.lid', 0x2d, 0x2, 0x24, 'formulae'))
# write_to_csv('events.csv', read_groups('81e00610.v7.lid', 0x2, 0x31, 0x532, 'events'))
# write_to_csv('groups.csv', read_groups('81e00610.v7.lid', 0x2a, 0x5, 0x8b, 'groups'))
