# @authors: Jen Enriquez, Victoria Lu, Jiayi Wu, Yannis Zhu

from flask import flash
from datetime import date, datetime, timedelta

import cs304dbi as dbi
import os, bcrypt

def timedelta_to_time(td):
    return (datetime.min + td).time()

def formate_date(event):
    event['formatted_date'] = event['eventdate'].strftime('%b %-d, %Y')
    start_time = timedelta_to_time(event['starttime'])
    end_time = timedelta_to_time(event['endtime'])
    event['formatted_starttime'] = start_time.strftime('%-I%p').lower().replace(':00', '')
    event['formatted_endtime'] = end_time.strftime('%-I:%M%p').lower().replace(':00', '')
    return event

def insert_event_data(conn, organizer_id, username, user_email, event_name, 
                        event_type, short_description, event_date, start_time, end_time, 
                        event_location, rsvp, event_tags, full_description, 
                        contact_email, pathname):
    curs = dbi.dict_cursor(conn)
    '''
    Inserts event information into the database.
    Returns the event_id of the inserted event. This is useful for inserting spam for a new event. 
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
        insert into eventcreated(organizerid, eventname, eventtype, shortdesc, eventdate, starttime, endtime, eventloc, rsvp, eventtag, fulldesc, contactemail, spam, numattendee)
        values (%s, %s, %s,%s, %s, %s,%s, %s, %s,%s, %s, %s, %s, 0);
        ''', [organizer_id, event_name, event_type, short_description,
            event_date, start_time, end_time, event_location,
            rsvp, event_tags, full_description, contact_email, pathname]
    )
    conn.commit() # Makes the change permanent

    curs.execute("select last_insert_id()")
    event_id = curs.fetchone()['last_insert_id()']
    return event_id

def insert_event_image(conn, event_id, pathname):
    '''
    Inserts pathname into the spam column a newly created event using last_insert_id
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        ''' 
        update eventcreated set spam = %s where eventid = %s;
        ''', [pathname, event_id]
    )
    conn.commit()
    return "Updated event image"

def get_events_by_user(conn, profile_userid, current_user_id):
    """
    Gets all events created by a specific user. 
    Used for displaying events that a user manages. 
    """
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        SELECT ec.*, acc.*, 
            IF(reg.participant IS NOT NULL AND reg.eventid = ec.eventid, 'yes', 'no') AS user_rsvped
        FROM eventcreated ec
        JOIN account acc ON ec.organizerid = acc.userid
        LEFT JOIN registration reg ON ec.eventid = reg.eventid 
                      AND reg.participant = %s
        WHERE reg.participant IS NOT NULL AND ec.organizerid = %s
            GROUP BY ec.eventid
        ORDER BY ec.eventdate, ec.starttime;
        """, [current_user_id, profile_userid]
    )
    events = curs.fetchall()
    for event in events:
        event = formate_date(event)
    return events

def get_homepage_events(conn, user_id=None):
    '''
    Gets all events in the database. 
    Used for viewing all events, filtering, and searching.
    '''
    curs = dbi.dict_cursor(conn)
    if user_id is None:
        # If no user ID is provided, return events without RSVP information
        curs.execute('''
            select *
            from eventcreated, account
            where eventcreated.organizerid = account.userid
            order by eventcreated.eventdate, eventcreated.starttime
        ''')
    else:
        curs.execute('''
            SELECT ec.*, acc.*, 
                IF(reg.participant IS NOT NULL AND reg.eventid = ec.eventid, 'yes', 'no') AS user_rsvped
            FROM eventcreated ec
            JOIN account acc ON ec.organizerid = acc.userid
            LEFT JOIN registration reg ON ec.eventid = reg.eventid AND reg.participant = %s
            GROUP BY ec.eventid
            ORDER BY ec.eventdate, ec.starttime;
        ''', [user_id])
    events = curs.fetchall()
    for event in events:
        event = formate_date(event)
    return events

def get_event_by_id(conn, event_id, userid):
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        SELECT ec.*, acc.*, GROUP_CONCAT(reg.participant) as attendees, 
            IF(%s IN (SELECT participant FROM registration WHERE eventid = ec.eventid), 'yes', 'no') AS user_rsvped
        FROM eventcreated ec
        JOIN account acc ON ec.organizerid = acc.userid
        LEFT JOIN registration reg ON ec.eventid = reg.eventid
        WHERE ec.eventid = %s
        GROUP BY ec.eventid
        ''', [userid, int(event_id)]
    )
    event = curs.fetchone()
    event = formate_date(event)
    return event  # Returns a single event object or None if not found

def get_org_by_userid(conn, userid):
    '''
    Gets specfics org info of an org by their userid.
    Used for Org Profile. 
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        SELECT org_account.userid, org_account.eboard, org_account.orginfo, account.username, account.email 
        FROM org_account 
        JOIN account ON org_account.userid = account.userid 
        WHERE org_account.userid = %s;
        ''', [int(userid)])
    return curs.fetchone()  # Returns a single event object or None if not found

def get_user_by_userid(conn,userid):
    '''
    Gets specfics info of a user by their userid.
    Used for User Profile. 
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        SELECT userid, username, email 
        FROM account 
        WHERE userid = %s;
        ''', [int(userid)])
    user_info = curs.fetchone()

    # If the user exists, fetch the count of followed organizations
    if user_info:
        curs.execute(
            '''
            SELECT COUNT(*) as following_count 
            FROM person_interest 
            WHERE follower = %s;
            ''', [int(userid)])
        following_count = curs.fetchone()['following_count']
        user_info['following_count'] = following_count
    return user_info 

def get_eventsid_attending(conn, userid):
    '''
    Gets events user RSVPed to by userid.
    Used for User Profile. 
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        SELECT ec.*, acc.*, 
            IF(reg.participant IS NOT NULL AND reg.eventid = ec.eventid, 'yes', 'no') AS user_rsvped
        FROM eventcreated ec
        JOIN account acc ON ec.organizerid = acc.userid
        LEFT JOIN registration reg ON ec.eventid = reg.eventid 
                      AND reg.participant = %s
        WHERE reg.participant IS NOT NULL
            GROUP BY ec.eventid
        ORDER BY ec.eventdate, ec.starttime;
        ''', [userid]
    )
    events = curs.fetchall()
    for event in events:
        event = formate_date(event)
    return events

def get_usertype(conn, userid):
    '''
    Gets usertype by userid
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        select usertype from account where userid = %s
        ''', [userid])
    return curs.fetchone()

def follow(conn, userid, orgid):
    '''
    Allow User follow org
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''insert into person_interest (follower, followed) values (%s, %s);
        ''', [userid, orgid]
    )
    conn.commit()

def unfollow(conn, userid, orgid):
    """
    Removes followed org by orgid from user's person_interest table
    """
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        delete from person_interest
        where follower = %s and followed = %s
        """, [userid, orgid]
    )
    conn.commit()

def is_following(conn, follower, followed):
    curs = dbi.cursor(conn)
    curs.execute('''SELECT COUNT(*) FROM person_interest
                    WHERE follower = %s AND followed = %s''',
                 [follower, followed])
    count = curs.fetchone()[0]
    return count > 0


def get_filtered_events(conn, filters,userid):
    '''
    Gets events matching certain filters
    '''
    curs = dbi.dict_cursor(conn)

    #sample final query: 
    #select *
    #    from eventcreated where 
    #    eventdate = ... and eventtype = ... and (eventtag like ... or event tag like ...)
    #want to build this up from individual strings
    
    #initilize list of parameters to replace %s
    if userid is None:
        query = '''
        select eventcreated.*, account.*
        from eventcreated, account, registration
        where 1=1 and eventcreated.organizerid = account.userid and eventcreated.eventid = registration.eventid
        '''
        parameters = []
    else: 
        query = '''
        select eventcreated.*, account.*, IF(%s IN (SELECT participant FROM registration WHERE eventid = eventcreated.eventid), 'yes', 'no') AS user_rsvped
        from eventcreated, account, registration
        where 1=1 and eventcreated.organizerid = account.userid and eventcreated.eventid = registration.eventid
        '''
        parameters = [userid]

    #always start with select select * from eventcreated where...

    #first checks if the user used a date/type/tag/org_name filter at all
    #if not, do not want it in the query
    if filters.get('date'):
        query += ' and eventdate = %s'
        parameters.append(filters['date']) #get user input 

    if filters.get('type'): 
        query += ' and eventtype = %s'
        parameters.append(filters['type'])

    if filters.get('org_name'):
        #the event table does not have a column called org_name, it only has organizerid
        #checks if the org_name matches the username in the account table, then select events 
        #with a matching organizerid
        query += ' and organizerid in (select userid from account where username = %s)'
        parameters.append(filters['org_name'])
    
    tags_to_filter = filters.get('tags') #this is a list of tags inputted by the user
    if tags_to_filter: 
        #note: if the user selects career and academic as their tags, 
        #we assume that that the user wants to see events with the career tag or the academic tag
        #(not events with the the career tag and the academic tag simultaneously)
        tag_conditions = []

        #for each tag in the list, want to check if the eventtag colum contains that tag
        for tag in tags_to_filter: 
            tag_conditions.append("eventtag like %s")
            parameters.append('%{}%'.format(tag))
        
        #assemble the final string 
        query += ' and (' + ' or '.join(tag_conditions) + ')'   
    
    if filters.get('orgs_following'):
        query += ' and organizerid in (select followed from person_interest where follower = %s)'
        parameters.append(filters['uid'])

    query += 'group by eventcreated.eventid order by eventcreated.eventdate, eventcreated.starttime;'

    curs.execute(query, parameters)
    events = curs.fetchall()

    # Formatting the date for each event
    for event in events:
        event = formate_date(event)

    return events

def search_events(conn, search_term,userid = None):
    '''
    Gets all events whose event names match a search term
    '''
    curs = dbi.dict_cursor(conn)
    if userid is None:
        query = ''' select eventcreated.*, account.*, GROUP_CONCAT(participant) as attendees
                    from eventcreated, account, registration 
                    where eventname like %s and eventcreated.organizerid = account.userid and eventcreated.eventid = registration.eventid;'''
        curs.execute(query, ['%' + search_term + '%'])
    else:
        curs.execute(''' 
            SELECT ec.*, acc.*, 
                IF(%s IN (SELECT participant FROM registration WHERE eventid = ec.eventid), 'yes', 'no') AS user_rsvped
            FROM eventcreated ec
            JOIN account acc ON ec.organizerid = acc.userid
            LEFT JOIN registration reg ON ec.eventid = reg.eventid AND reg.participant = %s
            WHERE ec.eventname like %s
            GROUP BY ec.eventid
            ORDER BY ec.eventdate, ec.starttime;
        ''', [userid, userid, '%' + search_term + '%'])
    events = curs.fetchall()
    for event in events:
        event = formate_date(event)
    return events

def update_event(conn, formData, eventID):
    """
    Updates event with info gathered info from form.
    Returns the full updated event dictionary
    """
    curs = dbi.dict_cursor(conn)
    
    #update an event with new data
    curs.execute(
        """
        update eventcreated
        set eventname = %s, shortdesc = %s,eventdate = %s,starttime = %s,
            endtime = %s,eventloc = %s,rsvp = %s,eventtag = %s,fulldesc = %s
        where eventid = %s;
        """, [formData.get('event_name'), formData.get('short_desc'),formData.get('event_date'), formData.get('start_time'),
            formData.get('end_time'), formData.get('event_location'),formData.get('rsvp_required'),formData.get('event_tags'),formData.get('full_desc'), eventID]
    )
    conn.commit()
    eventDict = get_event_by_id(conn,eventID)
    return eventDict

def get_followed_orgs(conn, userid): 
    '''Gets a list of orgs that a personal account is following
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''select org_account.userid, account.username
            from org_account inner join person_interest on person_interest.followed = org_account.userid
            inner join account on org_account.userid = account.userid
            where person_interest.follower = %s;''', [userid])
    return curs.fetchall()

#just gets info from account table, doesnt get personal or org specific data
def get_account_info(conn, userID):
    """
    Gets basic account info with the given account ID
    This info includes userid, username, usertype, and email (does not include hashed passwd)
    """
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        select userid, username, usertype, email from account
        where userid = %s;
        """, [userID]
    )
    return curs.fetchone()

def delete_event(conn, eventID):
    """
    Removes event with given id from the database
    """
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        delete from eventcreated
        where eventid = %s;
        """, [eventID]
    )
    conn.commit() # Makes the deletion permanent

def rsvp_required(conn, event_id):
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''select rsvp from eventcreated where eventid = %s
        ''', [event_id]
    )
    return curs.fetchone()

def user_rsvp_status(conn, event_id, user_id):
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        select * from registration where eventid = %s and participant = %s;
        ''', [event_id, user_id]
    )
    return curs.fetchone() 

def count_numattendee(conn, event_id):
    '''count number of attendees after user rsvp'd'''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''select count(participant) from registration where eventid = %s''', [event_id]
    )
    count = curs.fetchone()
    count = int(count.get('count(participant)'))
    return count

def rsvp(conn, event_id, user_id):
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''insert into registration (eventid, participant) values (%s, %s);
        ''', [event_id, user_id]
    )
    conn.commit()
    return 'Registration inserted'

def cancel_rsvp(conn, event_id, user_id):
    '''Deletes a rsvp record from the resgitration table
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute('delete from registration where eventid= %s and participant = %s;', [event_id, user_id])
    conn.commit()
    return "RSVP cancelled"

def update_numattendee(conn,eventid,count):
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''update eventcreated set numattendee = %s where eventid = %s;''',[count,eventid]
    )
    conn.commit()
    return 'updated number of attendees'

def is_valid_filename(filename):
    #filename pattern needs to match something like uploads/10_1700612634.png (id_timestamp.extension)
    parts = filename.split('_') 
    potential_uid = parts[0].split('/')[1]
    potential_timestamp = parts[1].split('.')[0]

    #flash(f'{parts}')
    #flash(f'{potential_uid}')
    #flash(f'{potential_timestamp}')

    #check if the filename has at least two parts
    if len(parts) != 2:
        return False
    #check if the first and second parts are numbers
    if not (potential_uid.isdigit() and potential_uid.isdigit()): 
        return False
    return True 

def get_rsvp_info(conn, event_id):
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''select eventid, userid, username, email from registration 
        inner join account on (registration.participant = account.userid) 
        where registration.eventid = %s;
        ''', [event_id]
    )
    return curs.fetchall()

######### helpers related to changing account information ######### 
def update_account(conn, formData, userID):
    """
    Updates account with info gathered info from form.
    Returns the full updated account dictionary
    """
    curs = dbi.dict_cursor(conn)
    

    if (get_account_info(conn,userID).get('usertype') == 'personal'):
        #update an account with new data
        curs.execute(
            """
            update account
            set username = %s, email = %s
            where userid = %s;
            """, [formData.get('username'), formData.get('email'), userID]
        )
        conn.commit()
    else: # the usertype must be org
        curs.execute(
            """
            update account
            set username = %s, email = %s
            where userid = %s;
            """, [formData.get('username'), formData.get('email'), userID]
        )
        curs.execute(
            """
            update org_account
            set eboard = %s, orginfo = %s
            where userid = %s;
            """, [formData.get('eboard'), formData.get('org_info'), userID]
        )
        conn.commit()

    accountDict = get_account_info(conn,userID)
    return accountDict

def update_password(conn, passwd, userID):
    """
    Updates account with info gathered info from form.
    Returns the full updated account dictionary
    """
    curs = dbi.dict_cursor(conn)
    hashed = bcrypt.hashpw(passwd.encode('utf-8'),
                           bcrypt.gensalt())
    
    #update an account with new data
    curs.execute(
        """
        update account
        set hashedp = %s
        where userid = %s;
        """, [hashed, userID]
    )
    conn.commit()

######### helpers related to Q&A feature #########
def insert_question(conn, event_id, user_id, question_content):
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        INSERT INTO QA (eventid, userid, question, questionDate)
        VALUES (%s, %s, %s, NOW());
    ''', [event_id, user_id, question_content])
    conn.commit()

def get_qa(conn,event_id):
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT * from QA, account where eventid = %s and QA.userid = account.userid;
    ''', [event_id])
    return curs.fetchall()

def insert_answer(conn, qa_id, organization_id, answer_content):
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        UPDATE QA
        SET orgid = %s, answer = %s, answerDate = NOW()
        WHERE QAID = %s;
    ''', [organization_id, answer_content, qa_id])
    conn.commit()


if __name__ == '__main__':
    #database = 'weevent_db' #team db
    database = os.getlogin() + '_db'
    dbi.conf(database)
    conn = dbi.connect()
