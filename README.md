# db_manager.sh


## Overview

This is a utility to move AdaptiveCity sensor, sensor_type and BIM data between JSON files and PostgreSQL.
The corresponding table names are `sensors`, `sensor_types` and `bim`, in the database `acp_prod`.

Our strategy is, in general, to store our data as JSON objects. We could easily use an object store like MongoDB but
for greater flexibility we are using PostgreSQL tables with a `jsonb` column. Note that the object data is stored
in the JSON, but also we **promote** some properties into actual database columns (e.g. for `sensors`:
`acp_id`, `acp_ts`, `acp_end_ts`) to take advantage of PostgreSQL query capability and indexing.

In general the data table is assumed to have the structure:
```
<identifier>, acp_ts, acp_ts_end, <json info>
```
where the `<identifier>`, `acp_ts` and `acp_ts_end` properties will *also* appear in the `<json_info>`. API's normally only
need to deal with the `<json_info>` data (i.e. we are replicating an object store using JSON as the object format). The
*database columns* `acp_ts` and `acp_ts_end` are native PostgreSQL timestamps, while the corresponding property values in
the JSON object will be ACP standard timestamp strings as used throughout the platform e.g. "1606601561.5036056".

E.g. the `sensors` table is:
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

```
sudo apt install libpq-dev
```

As user `acp_prod` (database will default to `acp_prod`):

```
git clone https://github.com/AdaptiveCity/acp_db_manager
cd ~/acp_db_manager
python3 -m venv venv
source venv/bin/activate
python3 -m pip install pip --upgrade
python3 -m pip install wheel
python3 -m pip install -r requirements.txt
```

## `secrets/settings.json`

You will need to collect the `~acp_prod/acp_db_manager/secrets/` directory from another server.

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
        },
        "bim": {
            "table_name": "bim",
            "id":         "crate_id",
            "json_info":  "crate_info"
        }
    }

}
```
Note the `TABLES` structure allows custom names to be used for the identifier and JSON columns, and the `<tablename>`
given in the `db_manager.sh` commands is actually a key into the `TABLES` dictionary.

Test the install with:
```
./db_manager.sh --status
```
The table names are as in the `secrets/settings.json` file, and we have not created them, hence output:
```
--status--
Querying table sensors :
    Table sensors not found.
Querying table sensor_types :
    Table sensor_types not found.
Querying table bim :
    Table bim not found.
```

## Creating the PostgreSQL tables

These tables are effectively using PostgreSQL as a JSON object store, and we are 'promoting' timestamps out of the JSON
into native PostgreSQL TIMESTAMP values to simplify some queries. The intention is that the definitive data always remains the
JSON, and this is the information returned in API queries. For example, in future we may use PostGIS and promote lat/lng
coordinates from the underlying JSON objects, but the point of this is to speed up spatial queries which could equally have
been implemented (more slowly) using the properties within the JSON data. Currently we are not creating PostgreSQL indices - we
can do this when we have queries that would benefit from those, still without altering the strategy of the JSON object representing
the definitive information.

As user `acp_prod`:

```
cd ~/acp_db_manager
psql
```

At the `psql` prompt:
```
CREATE TABLE sensors (
acp_id character varying NOT NULL,
acp_ts TIMESTAMP,
acp_ts_end TIMESTAMP,
sensor_info jsonb
);

CREATE TABLE sensor_types (
acp_type_id character varying NOT NULL,
acp_ts TIMESTAMP,
acp_ts_end TIMESTAMP,
type_info jsonb
);

CREATE TABLE bim (
crate_id character varying NOT NULL,
acp_ts TIMESTAMP,
acp_ts_end TIMESTAMP,
crate_info jsonb
);
```

At this point `$ ./db_manager.sh --status` will output:
```
--status--
Querying table sensors :
    zero rows found
Querying table sensor_types :
    zero rows found
Querying table bim :
    zero rows found
```

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

## Initializing the tables

The method is to use `acp_db_manager` to extract the data as JSON files from another server and then import that into your
server. `acp_ttn_manager` can be used to collect The Things Network device registrations and merge that information into
the `sensors` table. E.g.:
```
./db_manager.sh --dbwrite sensors --jsonfile secrets/sensors_cdbb_2020-11-29.json
./db_manager.sh --dbwrite sensor_types --jsonfile secrets/sensor_types_cdbb_2020-11-29.json
./db_manager.sh --dbwrite bim --jsonfile secrets/BIM_cdbb_2020-11-29.json
./db_manager.sh --status
```
Output:
```
--status--
Querying table sensors :
    31 rows found
    31 unique acp_id identifers in table
    most recent update was: 2020-11-18 17:05:43.123000
    newest entry: elsys-ems-0503e4
Querying table sensor_types :
    9 rows found
    9 unique acp_type_id identifers in table
    most recent update was: 2020-11-13 13:17:16.123000
    newest entry: monnit-Temperature
Querying table bim :
    418 rows found
    418 unique crate_id identifers in table
    most recent update was: 2020-11-19 23:20:21.841919
    newest entry: HW1
```

Then collected the TTN device registration data using `acp_ttn_manager` and *merged* that into the `sensors`
table with:
```
./db_manager.sh --dbmerge sensors --jsonfile ../acp_ttn_manager/secrets/cambridge-sensor-network2_2020-11-29.json
./db_manager.sh --status sensors
--status--
Querying table sensors :
    64 rows found
    43 unique acp_id identifers in table
    most recent update was: 2020-11-29 12:23:12.703506
    newest entry: rad-wd-f7c5c9
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

### `db_manager.sh --dbwrite <tablename> --jsonfile <filename>`

Kind-of the inverse of `--dbread`.

So for a given json file e.g. `sensors.json`, a `--dbclear sensors` followed by `--dbwrite sensors --jsonfile sensors.json`
followed by `--dbread sensors --jsonfile sensors2.json`
should result in `sensors.json` and `sensors2.json` having the same content.

### `db_manager.sh --dbmerge<tablename> [--jsonfile <filename>]`

E.g. after downloading the TTN settings for an application using `acp_ttn_manager` we can merge those settings into
the ACP `sensors` table:
```
./db_manager.sh --dbmerge sensors --jsonfile ../acp_ttn_manager/secrets/cambridge-sensor-network2_2020-11-29.json
```

This is similar to a `--dbwrite` **except** each the data from the `--jsonfile` will be **merged** with the corresponding object
in the database. This is useful if the new json contains a new property for existing sensors, e.g. `ttn_settings` so these can be
combined with exising properties such as `acp_location` which may alrady be recorded for the sensor.

Note that every 'base level` property in the `--jsonfile` will overwrite the existing property for the same object in the
database, i.e. this is not a recursive 'deep' merge.
