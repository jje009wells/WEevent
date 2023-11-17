from flask import flash

import cs304dbi as dbi
import os

def insert_event_data(conn, formData):
    #TO DO: need to add some testing on this
    #TO DO: instead of user having to manually enter their ID and email, just get that info from the session
    curs = dbi.dict_cursor(conn)
    curs.execute( # insert given movie into movie table
        '''
        insert into eventcreated(eventid, organizerid, eventname, eventtype, shortdesc,eventdate,starttime,endtime,eventloc,rsvp,eventtag,fulldesc,contactemail,spam)
        values (0, %s, %s, %s,%s, %s, %s,%s, %s, %s,%s, %s, %s,%s);
        ''', [formData.get('organizer_id'), formData.get('event_name'), formData.get('event_type'), formData.get('short_desc'),
            formData.get('event_date'),formData.get('start_time'),formData.get('end_time'),formData.get('event_location'),
            formData.get('rsvp_required'),formData.get('event_tags'),formData.get('full_desc'),formData.get('contact_email'),formData.get('event_image')]
    )
    conn.commit() # Makes the change permanent
    #TO DO: we can change this later, but returns name of event added for now for testing purposes
    return 'You just added {name} of type {type}'.format(name=formData.get('event_name'), type=formData.get('event_type'))

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
    #database = 'weevent_db' #team db
    database = os.getlogin() + '_db'
    dbi.conf(database)
    conn = dbi.connect()

    