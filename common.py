import struct
import csv

PAGE_SIZE=4096

def quotechars(chars):
    return ''.join( ['.', c][c.isalnum()] for c in chars)

def hexdump(chars, sep, width):
    while chars:
        line = chars[:width]
        chars = chars[width:]
        line = line.ljust( width, '\000' )
        print "%s%s%s" % (sep.join( "%02x" % ord(c) for c in line ),
                          sep, quotechars(line))

def pack_text(text):
    # Won't be fun if all goes well.. so here we might get empty texts, if so
    # we just need to update the length field to the length of the length
    # field. See catalog proposal document if you don't get this.

    if text == None or len(text) == 0:
        text_bin = struct.pack(">H", 2)
    else:
        l = len(text) + 1 + 2 # a null byte included

        if l % 2 != 0:
            l += 2 - l % 2

        text_bin = struct.pack(">H%ds" % (l - 2), l, text)

    return text_bin

def pad16(dump):
    # default is 16 bit length, the old formula structure had a bug, mentioning
    # it as 32 bit structure length
    tlen = len(dump) + 2
    plen = 0
    if tlen % 16 != 0:
        plen = 16 - tlen % 16;
        tlen += plen

    slen = struct.pack(">H", tlen)

    padding = struct.pack("%dx" % (plen))

    return slen + dump + padding

def pad_page(dump, page_size):
    if len(dump) % page_size != 0:
        # pad the remaining page
        dump += struct.pack("%dx" % (PAGE_SIZE - len(dump) % PAGE_SIZE))

        return dump

def read_string(dump):
    nlen = struct.unpack_from(">H", dump)[0]

    if nlen == 0:
        print """ERROR: A string length can never be zero, it should be atleast of
length 2, which will always include the length of the length field.
Please check your offsets"""
        exit(1)

    name = struct.unpack_from(">%ds" % (nlen - 2), dump[2:])

    return name[0], nlen

def write_to_csv(csv_file, dict_list):
    f = open(csv_file, 'wt')
    try:
        writer = csv.writer(f)
        # dump the header
        writer.writerow((dict_list[0].keys()))
        for d in dict_list:
            writer.writerow((d.values()))
    finally:
        f.close()
