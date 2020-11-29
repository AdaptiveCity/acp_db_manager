import psycopg2

class DBConn(object):

    def __init__(self, settings):
        self.settings = settings
        self.connect()
        self.cursor()

    def connect(self):
        self.con = psycopg2.connect(database=self.settings["PGDATABASE"],
                                    user=self.settings["PGUSER"])

    def cursor(self):
        self.cur = self.con.cursor()

    def close(self):
        self.con.close()

    # Query the database and return the results
    def dbread(self, query, query_args):
        #print("reading query: {}, query_args: {}".format(query, query_args))
        self.cur.execute(query, query_args)
        rows = self.cur.fetchall()
        return rows

    # Execute the write query and commit the results
    def dbwrite(self, query, data):
        self.cur.execute(query, data)
        self.con.commit()
