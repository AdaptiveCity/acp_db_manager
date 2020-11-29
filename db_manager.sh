#!/usr/bin/env python3

import argparse
import os, sys
import json

from classes.db_manager import DBManager

DEBUG = True


####################################################################
# Load settings
####################################################################
def load_settings():
    EXECDIR = os.path.abspath(os.path.dirname(sys.argv[0]))
    with open(EXECDIR+'/secrets/settings.json', 'r') as settings_file:
        settings_data = settings_file.read()

    # parse file
    settings = json.loads(settings_data)
    return settings

####################################################################
# Set up argument parsing
####################################################################

def parse_init():
    parser = argparse.ArgumentParser(description='Import/export json data <-> PostgreSQL')
    parser.add_argument('--jsonfile',
                        nargs='?',
                        metavar='<filename>',
                        help='JSON file for import or export')
    parser.add_argument('--id',
                        metavar='<identifier>',
                        help='Identifier to limit the scope e.g. (for --tablename sensors) "elsys-eye-044504".')
    parser.add_argument('--dbclear',
                        metavar='<tablename>',
                        default=None,
                        help='ERASE data from sensors table <tablename>, optional --id <identifier> for just that sensor')
    parser.add_argument('--status',
                        nargs='?',
                        metavar='<tablename>',
                        const='all',
                        help='Report status of database with optional tablename')
    command_group = parser.add_mutually_exclusive_group()
    command_group.add_argument('--dbwrite',
                        metavar='<tablename>',
                        default=None,
                        help='Import jsonfile -> PostgreSQL')
    command_group.add_argument('--dbread',
                        metavar='<tablename>',
                        default=None,
                        help='Export most recent PostgreSQL records from table -> jsonfile (or stdout if no jsonfile)')
    command_group.add_argument('--dbreadall',
                        metavar='<tablename>',
                        default=None,
                        help='Export ALL records from PostgreSQL table -> jsonfile (or stdout if no jsonfile)')
    command_group.add_argument('--dbmerge',
                        metavar='<tablename>',
                        default=None,
                        help='Read records from jsonfile (or stdin if no jsonfile) and SHALLOW MERGE base properties into matching PostgrSQL records')
    return parser

####################################################################
#
# Main
#
####################################################################

if __name__ == '__main__':

    parser = parse_init()
    args = parser.parse_args()

    settings = load_settings()

    db_manager = DBManager(settings)

    # --dbclear <tablename>: Empty table
    if args.dbclear:
        try:
            dbtable = settings["TABLES"][args.dbclear]
            db_manager.db_clear(dbtable, args.id)
        except KeyError:
            print("--dbclear <tablename> argument not recognized ({})".format(args.dbclear),file=sys.stderr,flush=True)
            sys.exit(1)
        sys.exit(1)

    # --status ['all'|<tablename>]
    if args.status:
        print('--status--')
        if args.status == 'all':
            for table_key in settings["TABLES"]:
                dbtable = settings["TABLES"][table_key]
                db_manager.db_status(dbtable, args.id)
        else:
            try:
                dbtable = settings["TABLES"][args.status]
                db_manager.db_status(dbtable, args.id)
            except KeyError:
                print("--status <tablename> argument not recognized ({})".format(args.status),file=sys.stderr,flush=True)
                sys.exit(1)
        sys.exit(0)

    # --dbread <tablename> [--jsonfile <filename.json>]
    if args.dbread:
        try:
            dbtable = settings["TABLES"][args.dbread]
            db_manager.db_read(args.jsonfile, dbtable, args.id)
        except KeyError:
            print("--dbread <tablename> argument not recognized ({})".format(args.dbread),file=sys.stderr,flush=True)
            sys.exit(1)
        exit(0)

    # --dbreadall <tablename> [--jsonfile <filename.json>]
    elif args.dbreadall:
        try:
            dbtable = settings["TABLES"][args.dbreadall]
            db_manager.db_readall(args.jsonfile, dbtable, args.id)
        except KeyError:
            print("--dbreadall <tablename> argument not recognized ({})".format(args.dbreadall),file=sys.stderr,flush=True)
            sys.exit(1)
        exit(0)

    # --dbwrite <tablename> --jsonfile <filename.json>
    elif args.dbwrite:
        try:
            dbtable = settings["TABLES"][args.dbwrite]
            db_manager.db_write(args.jsonfile, dbtable, args.id)
        except KeyError:
            print("--dbwrite <tablename> argument not recognized ({})".format(args.dbwrite),file=sys.stderr,flush=True)
            sys.exit(1)
        exit(0)

    # --dbmerge <tablename> --jsonfile <filename.json>
    elif args.dbmerge:
        try:
            dbtable = settings["TABLES"][args.dbmerge]
            db_manager.db_merge(args.jsonfile, dbtable, args.id)
        except KeyError:
            print("--dbmerge <tablename> argument not recognized ({})".format(args.dbmerge),file=sys.stderr,flush=True)
            sys.exit(1)
        exit(0)

    else:
        print("Command option not recognized",file=sys.stderr,flush=True)
