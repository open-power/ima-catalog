## Catalog generation and dump ##

### How to ###
In order to generate a new lid:

```
$ python read.py v8.lid
```

This generates three csv files namely `events.csv`, `groups.csv`, and `formulae.csv`.

Make changes to these csv files if required and generate the new catalog using
the following command.

```
$ python catalog.py <version of the new catalog> <old_lid> <new_file_prefix>
```
E.g.

```
$ python catalog.py 8 v8.lid e8100619_test
```

This generates a new lid file named e8100619_test.lid and a new dts file named e8100619_test.dts
using the csv files previously generated.

Note: Use the same lid file as the old lid (or one which has the same schema) which was used to 
generate the csv files.

---

### Revision History ###

##### v1 #####

 * Initial catalog generation from CSV files and dumping catalog into CSV files

#### v2 ####

 * Add support to generate DTS file from the catalog lid
