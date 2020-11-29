# db_manager.sh

This is a utility to move AdaptiveCity sensor metadata and sensor_type metadata between JSON files and PostgreSQL.

Our strategy is, in general, to store our data as JSON objects. We could easily use an object store like MongoDB but
for greater flexibility we are using PostgreSQL tables with a `jsonb` column. Note that the object data is stored
in the JSON, but also we **promote** some properties into actual database columns (e.g. for `sensors`:
`acp_id`, `acp_ts`, `acp_end_ts`) to take advantage of PostgreSQL query capability and indexing.

In general the data table is assumed to have the structure:
```
<identifier>, acp_ts, acp_ts_end, <json info>
```
the `sensors` table is:
```
acp_id, acp_ts, acp_ts_end, sensor_info
```

Records are added cumulatively to the table so that a record is kept of changes to a given sensor. The `acp_ts` timestamp
can be included with the incoming data, or db_manager.sh will use `now()` and the previous record for that sensor (if it exists)
 will have that value set as its `acp_ts_end`. The new record with have `acp_ts_end` as `NULL`.

Consequently, the basic:
```
db_manager.sh --dbread sensors
```
which reads the database and outputs JSON is coded to only extract the lastest
record for each sensor / sensor_type, returned as a json *object* with the `acp_id` as property names. If the entire history is
required then:
```
db_manager.sh --dbreadall sensors
```
command can be used and the result will be a json *list*.

## Installation

(will be added to `acp_data_strategy` readme)

```
sudo apt install libpg-dev
```

As user `acp_prod` (database will default to `acp_prod`):

```
psql

CREATE TABLE public.sensors (
    acp_id character varying NOT NULL,
    acp_ts TIMESTAMP,
    acp_ts_end TIMESTAMP,
    sensor_info jsonb
);

```

```
cd ~/acp_data_strategy
source venv/bin/activate
python3 -m pip install psycopg2
```

## `secrets/settings.json`

You will need to collect the `~acp_prod/acp_data_strategy/db_manager/secrets/` directory from another server.

The `settings.json` content currently is as below, note as the `acp_prod` user you do not need the `PGPASSWORD`:
```
{
    "PGHOST": "127.0.0.1",
    "PGDATABASE": "acp_prod",
    "PGUSER": "acp_prod",
    "PGPASSWORD": "",
    "PGPORT": "5432",

    "TABLES": {
        "sensors": {
            "table_name": "sensors",
            "id":         "acp_id",
            "json_info":  "sensor_info"
        },
        "sensor_types": {
            "table_name": "sensor_types",
            "id":         "acp_type_id",
            "json_info":  "type_info"
        }
    }

}
```
Note the `TABLES` structure allows custom names to be used for the identifier and JSON columns, and the `<tablename>`
given in the `db_manager.sh` commands is actually a key into the `TABLES` dictionary.

## Command line usage of `db_manager.sh`

```
cd ~/acp_data_strategy/db_manager
source ../venv/bin/activate

./db_manager.sh --help

usage: db_manager.sh [--help] [--jsonfile <filename>] [--id <identifier>]
            (--status [<tablename>]  |
             --dbread <tablename>    |
             --dbreadall <tablename> |
             --dbwrite <tablename>   |
             --dbmerge <tablename>   |
             --dbclear <tablename>)

Import/export json data <-> PostgreSQL

optional arguments:
  -h, --help            show this help message and exit
  --jsonfile <filename>
                        JSON file for import or export
  --id <identifier>     Identifier to limit the scope e.g. (for --tablename sensors) "elsys-eye-044504".
  --dbclear <tablename>
                        ERASE data from sensors table <tablename>, optional --id <identifier> for just that sensor
  --status [<tablename>]
                        Report status of database with optional tablename
  --dbwrite <tablename>
                        Import jsonfile -> PostgreSQL
  --dbread <tablename>  Export most recent PostgreSQL records from table -> jsonfile (or stdout if no jsonfile)
  --dbreadall <tablename>
                        Export ALL records from PostgreSQL table -> jsonfile (or stdout if no jsonfile)
  --dbmerge <tablename>
                        Read records from jsonfile (or stdin if no jsonfile) and SHALLOW MERGE base properties into
                        matching PostgrSQL records
```

## Examples

### `db_manager.sh --status [<tablename>]`

Reports some general status of the given database table (e.g. number of rows, most recent update).

As in all examples, `<tablename>` is actually a key in `settings.json` which does not necessarily equate to the names of
actual tables in the database.

Current table references include `sensors` and `sensor_types` but others will be added.

### `db_manager.sh --dbclear <tablename> [--id <identifier>]`

WARNING: removes ALL rows from the table if no `--id` is given.

If an identifier is given (i.e. an `acp_id` or `acp_type_id`) then only the records for that item will be removed.

### `db_manager.sh --dbread <tablename> [--jsonfile <filename>] [--id <identifier>`]

READS the database table, returning a json object with a property-per-sensor (or sensor_type)

If no `--jsonfile <filename>` is given, the command writes to stdout.

Note the table can contain multiple timestamped records with the same identifier and this command will return the most
recent in each case. I.e. for the `sensors` table then most recent sensor metadata will be returned for each sensor.

If an `--id` is given, then only the latest data for that identifier will be returned.

### `db_manager.sh --dbreadall <tablename> [--jsonfile <filename>] [--id <identifier>`]

Like `--dbread`, but returns **all** the records in the database table, not only the most recent for each
sensor / sensor_type. I.e. for each sensor multiple records may be returned, with different `acp_ts` values.

Consequently the json returned is a *json list*, not a json object with a property-per-sensor/sensor_type.

### `db_manager.sh --dbwrite <tablename> [--jsonfile <filename>]

Kind-of the inverse of `--dbread`.

So for a given json file e.g. `sensors.json`, a `--dbclear sensors` followed by `--dbwrite sensors --jsonfile sensors.json`
followed by `--dbread sensors --jsonfile sensors2.json`
should result in `sensors.json` and `sensors2.json` having the same content.

### `db_manager.sh --dbmerge<tablename> [--jsonfile <filename>]`

This is similar to a `--dbwrite` **except** each the data from the `--jsonfile` will be **merged** with the corresponding object
in the database. This is useful if the new json contains a new property for existing sensors, e.g. `ttn_settings` so these can be
combined with exising properties such as `acp_location` which may alrady be recorded for the sensor.

Note that every 'base level` property in the `--jsonfile` will overwrite the existing property for the same object in the
database, i.e. this is not a recursive 'deep' merge.

# Accumulated background stuff

email ijl20 to Rohit 2020-10-14:

I'm in the process of doing something similar between the JSON files and postgresql to complete the acp_data_strategy
work using the data from postgresql rather than the files (as you had it in the prior iteration of acp_data_strategy).
I.e. see acp_data_strategy/db_testing and you'll see the work in progress.

I.e. the 'json' file format of our sensor and sensor_type data can act as a means of exchange of data between the database and TTN.

At the moment we have

acp_data_strategy/secrets/sensors.json
acp_data_strategy/secrets/sensor_types.json

both of which are JSON 'dictionaries' keyed on acp_id and acp_type_id respectively.

I am writing python/bash scripts that will import/export data from the tables from/to JSON files. I'll need to support
multiple methods for file <-> database, but in principle these are similar to file <-> ttn, e.g. I'll have something like:
```
sensors_write.py <sensors json file name>:

              sensors json file -> WRITE each sensor object to sensors db table,
                                             overwrite if already there.

sensors_merge.py <sensors json file name>:
              sensors json file -> MERGE each sensor object into db table,
                                              keep existing properties if they're not overwritten

sensors_read <sensors json file name>:
              read all sensors from DB & export to (optional) JSON file / stdout

sensor_read <acp_id> <sensors json file name>:
             read a single sensor from DB, and write it into (optional, existing) sensors json file
             If the <sensor json file> isn't given, then write to stdout.

sensor_delete <acp_id>:
             deletes that sensor from the database
```
So pretty basic, but should form a useful set of scripts for the database (me) and TTN (you) with JSON files in
the middle, and in due course we'll add the capability of going straight database <-> ttn but the file scripts will still be useful.
