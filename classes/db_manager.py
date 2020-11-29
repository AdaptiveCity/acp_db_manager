
############################################################
# Json file <-> PostgreSQL command-line utility class      #
############################################################

import json
import sys
from datetime import datetime
import copy # used for deepcopy
from classes.dbconn import DBConn

DEBUG = True

"""
Reads/writes DB table: <id>,acp_ts,acp_ts_end,<json_info>

The <id> and <json_info> column names are defined in settings.json.

E.g. 'sensors' table is acp_id,acp_ts,acp_ts_end,sensor_info.
"""

class DBManager(object):

    def __init__(self, settings):
        self.settings = settings

    ####################################################################
    # Clear database
    ####################################################################
    def db_clear(self, db_table, id):
        where = " WHERE "+db_table["id"]+"='"+id+"'" if id else ""
        db_conn = DBConn(self.settings)
        query = "DELETE FROM {} {}".format(db_table["table_name"], where)
        db_conn.dbwrite(query,None)

    ####################################################################
    # Report database status
    ####################################################################
    def db_status(self, db_table, id):
        # Get table properties from settings.json
        table_name = db_table["table_name"]
        id_name = db_table["id"]
        json_name = db_table["json_info"]

        # General 'WHERE' clause if --id given
        where = " WHERE "+id_name+"='"+id+"'" if id else ""

        # Build/execute query for record count
        print(f'Querying table {table_name} {where}:')
        db_conn = DBConn(self.settings)
        query = f'SELECT COUNT(*) FROM {table_name} {where}'
        count = db_conn.dbread(query,None)[0][0]
        if count == 0:
            print("    zero rows found")
        else:
            print("    {} rows found".format(count))

            # Get count of unique identifiers (acp_ts_end IS NULL)
            # if --id NOT given
            if not id:
                query = f'SELECT COUNT(*) FROM {table_name} WHERE acp_ts_end IS NULL'
                count = db_conn.dbread(query,None)[0][0]
                print(f'    {count} unique {id_name} identifers in table')

            # Build/execute query for max_ts
            query = f'SELECT MAX(acp_ts) FROM {table_name} {where}'
            max_ts = db_conn.dbread(query,None)[0][0]
            print(f'    most recent update was: {max_ts}')

            # Build/execute query for row with newest acp_ts
            if id:
                where = f"WHERE {id_name} = '{id}' AND acp_ts_end IS NULL"
                query = f"SELECT {id_name},acp_ts,{json_name} FROM {table_name} {where}"
            else:
                where = f"WHERE acp_ts = (SELECT MAX(acp_ts) from {table_name})"
                query = f"SELECT {id_name},acp_ts,{json_name} from {table_name} {where}"

            # Set up return values from first row with newest acp_ts returned.
            ret_id, ret_acp_ts, ret_info = db_conn.dbread(query,None)[0]
            print(f"    newest entry: {ret_id}")

    ###################################################################################################################
    # write_obj - inserts a new database object record (used by db_write, db_merge)
    #   db_conn:       the database connection
    #   id:            the object identifier, e.g. "ijl20-sodaq-ttn"
    #   json_info_obj: the JSON information payload defining object
    #   db_table:      the 'TABLES' object from settings.json that gives the column names
    #   merge:         boolean that controls whether to "write" the json_info_obj or "merge" it into existing record.
    ###################################################################################################################
    def write_obj(self, db_conn, id, json_info_obj, db_table, merge=False):
        table_name = db_table["table_name"]
        id_name = db_table["id"]
        json_name = db_table["json_info"]
        # Create a datetime version of the "acp_ts" record timestamp
        if "acp_ts" in json_info_obj:
            update_acp_ts = datetime.fromtimestamp(float(json_info_obj["acp_ts"]))
        else:
            update_acp_ts = datetime.now()
            json_info_obj["acp_ts"] = '{:.6f}'.format(datetime.timestamp(update_acp_ts))

        # Update existing record 'acp_ts_end' (currently NULL) to this acp_ts (ONLY IF NEW acp_ts is NEWER)
        # First get acp_ts of most recent entry for current is
        query = f'SELECT acp_ts,{json_name} FROM {table_name} WHERE {id_name}=%s AND acp_ts_end IS NULL'
        query_args = (id,)
        r = db_conn.dbread(query, query_args)
        # Go ahead and update/insert if no records found or this record is newer than most recent
        if len(r) == 0 or r[0][0] < update_acp_ts:
            # Update (optional) existing record with acp_ts_end timestamp
            #DEBUG HERE WE WANT TO UPDATE acp_ts_end in the OBJECT
            update_json_info = {}
            if len(r) == 1:
                update_json_info = copy.deepcopy(r[0][1])
                # Add "acp_ts_end" timestamp to json info of previous record
                update_json_info.update( { 'acp_ts_end': '{:.6f}'.format(datetime.timestamp(update_acp_ts)) } )
                # Update (optional) existing record with acp_ts_end timestamp
                query = f'UPDATE {table_name} SET acp_ts_end=%s, {json_name}=%s WHERE {id_name}=%s AND acp_ts_end IS NULL'
                query_args = (update_acp_ts, json.dumps(update_json_info), id)
                db_conn.dbwrite(query, query_args)

            if merge and len(r) == 1:
                update_json_info.update(json_info_obj)
                del update_json_info["acp_ts_end"]
            else:
                update_json_info = json_info_obj

            # Add new entry with this acp_ts
            query = f'INSERT INTO {table_name} ({id_name}, acp_ts, {json_name})'+" VALUES (%s, %s, %s)"
            query_args = ( id, update_acp_ts, json.dumps(update_json_info))
            try:
                db_conn.dbwrite(query, query_args)
            except:
                if DEBUG:
                    print(sys.exc_info(),flush=True,file=sys.stderr)
        else:
            print(f'Skipping {id} (existing or newer record in table)',flush=True,file=sys.stderr)

    ####################################################################
    # db_write Import JSON -> Database
    ####################################################################
    def db_write(self, json_filename, db_table, id):
        try:
            with open(json_filename, 'r') as json_sensors:
                sensors_data = json_sensors.read()
        except FileNotFoundError:
            print("db_write --jsonfile not found: {}".format(json_filename),flush=True,file=sys.stderr)
            exit(1)

        # parse file { "<id>" : { "<id_name>: "<id", ...} }
        obj_list = json.loads(sensors_data)

        print("db_write loaded: {}".format(json_filename),flush=True,file=sys.stderr)

        db_conn = DBConn(self.settings)

        if id:
            if id in obj_list:
                self.write_obj(db_conn, id, obj_list[id], db_table)
            else:
                print("db_write --id '{}' not found in json file".format(id),flush=True,file=sys.stderr)
                exit(1)
            exit(0)

        # No --id given then iterate through all objects in json file
        for obj_id in obj_list:
            self.write_obj(db_conn, obj_id, obj_list[obj_id], db_table)

    ####################################################################
    # db_merge Merge JSON -> Database
    ####################################################################
    def db_merge(self, json_filename, db_table, id):
        with open(json_filename, 'r') as json_sensors:
            json_data = json_sensors.read()

        # parse file { "<id>" : { "<id_name>: "<id", ...} }
        obj_list = json.loads(json_data)

        print("db_merge loaded {}".format(json_filename),flush=True,file=sys.stderr)

        db_conn = DBConn(self.settings)

        if id:
            if id in obj_list:
                self.write_obj(db_conn, id, obj_list[id], db_table, merge=True)
            else:
                print("db_merge --id '{}' not found in json file".format(id),flush=True,file=sys.stderr)
                exit(1)
            exit(0)

        # No --id given then iterate through all objects in json file
        for obj_id in obj_list:
            self.write_obj(db_conn, obj_id, obj_list[obj_id], db_table, merge=True)

    ####################################################################
    # db_read Export database -> JSON (latest records only)
    ####################################################################
    def db_read(self, json_filename, db_table, id):
        db_conn = DBConn(self.settings)

        if id:
            # To select the latest object for id
            query = "SELECT {},{} FROM {} WHERE acp_ts_end IS NULL AND {}='{}'".format(
                        db_table["id"],
                        db_table["json_info"],
                        db_table["table_name"],
                        db_table["id"],
                        id)
        else:
            # To select *all* the latest sensor objects:
            query = "SELECT {},{} FROM {} WHERE acp_ts_end IS NULL".format(
                        db_table["id"],
                        db_table["json_info"],
                        db_table["table_name"])

        try:
            result_obj = {}
            rows = db_conn.dbread(query, None)
            for row in rows:
                id, json_info = row
                result_obj[id] = json_info

            self.write_json(result_obj, json_filename)

        except:
            if DEBUG:
                print(sys.exc_info(),flush=True,file=sys.stderr)

    ####################################################################
    # db_read Export database -> JSON (latest records only)
    ####################################################################
    def db_readall(self, json_filename, db_table,id):
        db_conn = DBConn(self.settings)
        # To select *all* the latest sensor objects:
        if id:
            # To select the latest object for id
            query = "SELECT {},{} FROM {} WHERE {}='{}'".format(
                        db_table["id"],
                        db_table["json_info"],
                        db_table["table_name"],
                        db_table["id"],
                        id)
        else:
            # To select *all* the latest sensor objects:
            query = "SELECT {},{} FROM {}".format(
                        db_table["id"],
                        db_table["json_info"],
                        db_table["table_name"])

        try:
            result_list = []
            rows = db_conn.dbread(query, None)
            for row in rows:
                id, json_info = row
                result_list.append( json_info )

            self.write_json(result_list, json_filename)

        except:
            if DEBUG:
                print(sys.exc_info(),flush=True,file=sys.stderr)

    ####################################################################
    # write_json: output a python dict to json file
    ####################################################################
    def write_json(self, json_obj, json_filename):
        with (open(json_filename,'w') if json_filename is not None else sys.stdout) as outfile:
            outfile.write(json.dumps(json_obj, sort_keys=True, indent=4)+'\n')

# End Class JsonDB
