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
sudo apt install libpg-dev
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
