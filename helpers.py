from flask import flash

import cs304dbi as dbi
import os

def get_all_events(conn):
    """
    This function gets a list of all event names in currently in the eventcreated table.
    """
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        select eventname from eventcreated;
        """
    )
    return curs.fetchall()


if __name__ == '__main__':
    database = os.getlogin() + '_db'
    dbi.conf(database)
    conn = dbi.connect()

    