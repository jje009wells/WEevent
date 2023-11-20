from flask import flash

import cs304dbi as dbi
import os

def insert_event_data(conn, organizer_id, username, user_email, event_name, event_type, short_description, event_date, start_time, end_time, event_location, rsvp, event_tags, full_description, contact_email, pathname):
    curs = dbi.dict_cursor(conn)
    '''
    This helper function inserts event information into the database
    '''

    #to avoid ref integrity issues, first insert data about the account
    #!!!will modify this code after enforcing login
    #for the sake of simplicity, 
    #if the organizer_id does not exist, populate the account table
    #if the organizer_id already exists, make no changes 

    #check if the organizer-id already exists
    curs.execute("select * from account where userid = %s", [organizer_id])
    existing_organizer = curs.fetchone()

    if existing_organizer is None:
        #if organizer does not exist, insert into the account table
        curs.execute(
            '''
            INSERT INTO account (userid, usertype, username, email)
            VALUES (%s, %s, %s, %s);
            ''', [organizer_id, event_type, username, user_email]
        )
    #make no changes if the organizer already exists

    #insert event information into the events table 
    curs.execute( 
        '''
        insert into eventcreated(organizerid, eventname, eventtype, shortdesc, eventdate, starttime, endtime, eventloc, rsvp, eventtag, fulldesc, contactemail, spam)
        values (%s, %s, %s,%s, %s, %s,%s, %s, %s,%s, %s, %s, %s);
        ''', [organizer_id, event_name, event_type, short_description,
            event_date, start_time, end_time, event_location,
            rsvp, event_tags, full_description, contact_email, pathname]
    )
    conn.commit() # Makes the change permanent
    return 'Event data inserted' 

def get_all_events(conn):
    """
    This function gets a list of all event names in currently in the eventcreated table.
    """
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        select eventname, eventid
        from eventcreated;
        """
    )
    return curs.fetchall()

def get_events_by_user(conn, userid):
    """
    """
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        select * from eventcreated where organizerid = %s;
        """, [userid]
    )
    return curs.fetchall()

def get_homepage_events(conn):
    '''
    This function gets a list of all event names in currently in the eventcreated table.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        select * from eventcreated;
        '''
    )
    return curs.fetchall()

def get_event_by_id(conn, event_id):
    '''
    This function retrieves the details of a specific event by its event_id.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        SELECT * FROM eventcreated WHERE eventid = %s;
        ''', [event_id]
    )
    return curs.fetchone()  # Returns a single event object or None if not found


def get_filtered_events(conn, filters):
    curs = dbi.dict_cursor(conn)

    #sample final query: 
    #select *
    #    from eventcreated where 
    #    eventdate = ... and eventtype = ... and (eventtag like ... or event tag like ...)
    #want to build this up from individual strings

    #always start with select select * from eventcreated where...
    query = '''
        select *
        from eventcreated where 1=1
        '''

    #initilize list of parameters to replace %s
    parameters = []

    #first checks if the user used a date/type/tag/org_name filter at all
    #if not, do not want it in the query
    if filters.get('date'):
        query += ' and eventdate = %s'
        parameters.append(filters['date'])

    if filters.get('type'):
        query += ' and eventtype = %s'
        parameters.append(filters['type'])

    if filters.get('org_name'):
        #the event table does not have a column called org_name, it only has organizerid
        #checks if the org_name matches the username in the account table, then select events 
        #with a matching organizerid
        query += ' and organizerid in (select userid from account where username = %s)'
        parameters.append(filters['org_name'])
    
    tags_to_filter = filters.get('tags') #this is a list of tags 

    if tags_to_filter: 

        #note: if the user selects career and academic as their tags, 
        #we assume that that the user want to see events with the career tag or  the academic tag
        #(not events with the the career tag and the academic tag simultaneously)
        tag_conditions = []

        #for each tag in the list, want to check if the eventtag colum contains that tag
        for tag in tags_to_filter: 
            tag_conditions.append("eventtag like %s")
            parameters.append('%{}%'.format(tag))
        
        #assemble the final string 
        query += ' and (' + ' or '.join(tag_conditions) + ')'   
    
    #add ; at the end of the final query
    query += ';'
     
    print("Query:", query)
    print("Parameters:", parameters)

    #get all the events matching the filters 
    curs.execute(query, parameters)

    return curs.fetchall()

def search_events(conn, search_term):
    curs = dbi.dict_cursor(conn)
    query = ''' select * from eventcreated where eventname like %s '''
    curs.execute(query, ['%' + search_term + '%'])
    return curs.fetchall()

def update_event(conn, formData, eventID):
    """
    Updates event with info gathered from form.
    Returns the full updated event dictionary
    """
    curs = dbi.dict_cursor(conn)
    #do some error checking first, then proceed with this:
    curs.execute(# Update movie with new data
        """
        update eventcreated
        set eventname = %s, eventtype = %s, shortdesc = %s,eventdate = %s,starttime = %s,
            endtime = %s,eventloc = %s,rsvp = %s,eventtag = %s,fulldesc = %s,spam = %s
        where eventid = %s;
        """, [formData.get('event_name'), formData.get('event_type'), formData.get('short_desc'),formData.get('event_date'), formData.get('start_time'),
            formData.get('end_time'), formData.get('event_location'),formData.get('rsvp_required'),formData.get('event_tags'),formData.get('full_desc'),formData.get('event_image'), eventID]
    )
    conn.commit()
    eventDict = event_details(conn,eventID)
    return eventDict

def event_details(conn, eventID):
    """
    Returns a dict with information about a given event based on the eventID
    """
    curs = dbi.dict_cursor(conn)
    curs.execute( # find the given movie
        '''
        select eventid, organizerid, eventname, eventtype, shortdesc,eventdate,starttime,endtime,eventloc,rsvp,eventtag,fulldesc,contactemail,spam
        from eventcreated
        where eventid = %s;
        ''', [eventID]
    )
    
    eventDict = curs.fetchone()  
    return eventDict

def get_event_by_id(conn, event_id):
    '''
    This function retrieves the details of a specific event by its event_id.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        SELECT * FROM eventcreated WHERE eventid = %s;
        ''', [event_id]
    )
    return curs.fetchone()  # Returns a single event object or None if not found

def delete_event(conn, eventID):
    """
    Remove event with given id from the database
    """
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        delete from eventcreated
        where eventid = %s;
        """, [eventID]
    )
    conn.commit() # Makes the deletion permanent


if __name__ == '__main__':
    #database = 'weevent_db' #team db
    database = os.getlogin() + '_db'
    dbi.conf(database)
    conn = dbi.connect()
