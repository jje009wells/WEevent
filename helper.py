from flask import (Flask, render_template, make_response, url_for, request,
                   redirect, flash, session, send_from_directory, jsonify)
from werkzeug.utils import secure_filename
app = Flask(__name__)


import weevent_db as dbi

def check_event(conn, event_id):
    '''Given a event from the form, 
    checks that the event-id of the event is not already in the database
    Return true if event exists in database already, false otherwise'''
    curs = dbi.dict_cursor(conn);
    curs.execute('''
                 SELECT event.name
                 FROM event 
                 WHERE event.id = %s ''',
                 [event_id])
    event = curs.fetchone();
    if event is None:
        return False
    return True


def insert(conn, event_id, organizer_id, event_name, event_type, short_desc, date_and_time):
    '''If the event does not already exist in the database,
    add the event into the table using the event-id, organizer-id, event-name, event-type, short-desc, and date-and-time'''
    curs = dbi.dict_cursor(conn)
    curs.execute('''INSERT into event(eventd, organizerid, eventname, eventtype, shortdesc, date_and_time)
            values(%s,%s,%s,%s);''',[int(event_id), int(organizer_id), event_name, event_type, short_desc, date_and_time])
    conn.commit() #commit changes
