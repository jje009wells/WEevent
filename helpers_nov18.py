# @authors: Jen Enriquez, Victoria Lu, Jiayi Wu, Yannis Zhu

from flask import flash
from datetime import date, datetime, timedelta

import cs304dbi as dbi
import os, bcrypt

#########  helpers related to getting events ######### 

def timedelta_to_time(td):
    '''
    Converts a timedelta object to a time object.
    Useful for converting the time stored in the database to a standard time format.
    '''
    return (datetime.min + td).time()

def formate_date(event):
    '''
    Formats the date and time of an event for display.
    Adds formatted date and time to the event dictionary.
    '''
    event['formatted_date'] = event['eventdate'].strftime('%b %-d, %Y')
    start_time = timedelta_to_time(event['starttime'])
    end_time = timedelta_to_time(event['endtime'])
    event['formatted_starttime'] = start_time.strftime('%-I%p').lower().replace(':00', '')
    event['formatted_endtime'] = end_time.strftime('%-I:%M%p').lower().replace(':00', '')
    return event

def get_events_by_user(conn, profile_userid, current_user_id):
    """
    Retrieves all events created by a specific user.
    Used for displaying events that a user manages.
    Includes RSVP information if the current user has RSVPed to the events.
    """
    curs = dbi.dict_cursor(conn)
    
    # Select * here as all columns are needed for rendering
    curs.execute(
        """
        select ec.eventid, ec.organizerid, ec.eventname, ec.eventtype, ec.shortdesc,
        ec.eventdate, ec.starttime, ec.endtime, ec.eventloc, ec.rsvp, ec.eventtag, ec.fulldesc,
        ec.contactemail, ec.spam, ec.numattendee, acc.userid as userid, acc.usertype, 
        acc.username, acc.email,
            IF(reg.participant IS NOT NULL AND reg.eventid = ec.eventid, 'yes', 'no') AS user_rsvped
        from eventcreated ec
        left join registration reg
        on reg.participant = %s
        join account acc
        on ec.organizerid = acc.userid
        where ec.organizerid = %s
        group by ec.eventid
        order by ec.eventdate, ec.starttime;
        """, [current_user_id, profile_userid]
    )
    events = curs.fetchall()
    for event in events:
        event = formate_date(event)
    return events

def get_homepage_events(conn, user_id=None):
    '''
    Retrieves all events in the database.
    Used for viewing all events, filtering, and searching.
    Includes RSVP information if a user ID is provided.
    '''
    curs = dbi.dict_cursor(conn)
    if user_id is None:
        # If no user ID is provided, return events without RSVP information
        
        # Select * here as all columns are needed for rendering 
        curs.execute('''
            select ec.eventid, ec.organizerid, ec.eventname, ec.eventtype, ec.shortdesc,
            ec.eventdate, ec.starttime, ec.endtime, ec.eventloc, ec.rsvp, ec.eventtag, ec.fulldesc,
            ec.contactemail, ec.spam, ec.numattendee, acc.userid as userid, acc.usertype, 
            acc.username, acc.email
            from eventcreated ec, account acc
            where ec.organizerid = acc.userid
            order by ec.eventdate, ec.starttime
        ''')
    else:
        curs.execute('''
            select ec.eventid, ec.organizerid, ec.eventname, ec.eventtype, ec.shortdesc,
            ec.eventdate, ec.starttime, ec.endtime, ec.eventloc, ec.rsvp, ec.eventtag, ec.fulldesc,
            ec.contactemail, ec.spam, ec.numattendee, acc.userid as userid, acc.usertype, 
            acc.username, acc.email,
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

def get_upcoming_events(events):
    '''
    Filters and returns upcoming events from a list of events.
    An event is considered upcoming if its date is equal to or greater than the current date.
    '''
    now = datetime.now().date()
    upcoming_events = [event for event in events if event['eventdate'] >= now]
    return upcoming_events


def get_event_by_id(conn, event_id, userid):
    '''
    Retrieves a specific event by its ID.
    Includes RSVP information and a list of attendees.
    Formats the event date and time for display.
    '''
    curs = dbi.dict_cursor(conn)
    # Select * here as all columns are needed for rendering
    curs.execute(
        '''
        select ec.eventid, ec.organizerid, ec.eventname, ec.eventtype, ec.shortdesc,
            ec.eventdate, ec.starttime, ec.endtime, ec.eventloc, ec.rsvp, ec.eventtag, ec.fulldesc,
            ec.contactemail, ec.spam, ec.numattendee, acc.userid as userid, acc.usertype, 
            acc.username, acc.email, acc.profile_pic, GROUP_CONCAT(reg.participant) as attendees, 
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
    Retrieves specific organization information by the user ID.
    Used for displaying organization profiles.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        SELECT org_account.userid, org_account.eboard, org_account.orginfo, account.username, account.email, account.profile_pic 
        FROM org_account 
        JOIN account ON org_account.userid = account.userid 
        WHERE org_account.userid = %s;
        ''', [int(userid)])
    return curs.fetchone()  # Returns a single event object or None if not found

def get_user_by_userid(conn,userid):
    '''
    Retrieves specific information of a user by their user ID.
    Used for displaying user profiles.
    Includes the count of organizations followed by the user.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        SELECT userid, username, email, profile_pic 
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
    Retrieves events that a user has RSVPed to by their user ID.
    Used for displaying events on a user's profile.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        select ec.eventid, ec.organizerid, ec.eventname, ec.eventtype, ec.shortdesc,
            ec.eventdate, ec.starttime, ec.endtime, ec.eventloc, ec.rsvp, ec.eventtag, ec.fulldesc,
            ec.contactemail, ec.spam, ec.numattendee, acc.userid as userid, acc.usertype, 
            acc.username, acc.email, 
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

#########  helpers related to inserting events ######### 
def insert_event_data(conn, organizer_id, username, user_email, event_name, 
                        event_type, short_description, event_date, start_time, end_time, 
                        event_location, rsvp, event_tags, full_description, 
                        contact_email, pathname):
    curs = dbi.dict_cursor(conn)
    '''
    Inserts new event information into the database.
    Handles the creation of a new organizer if not already existing.
    Returns the event ID of the newly inserted event.
    '''
    # Check if the organizer-id already exists
    curs.execute("select userid from account where userid = %s", [organizer_id])
    existing_organizer = curs.fetchone()

    if existing_organizer is None:
        # If organizer does not exist, insert into the account table
        curs.execute(
            '''
            INSERT INTO account (userid, usertype, username, email)
            VALUES (%s, %s, %s, %s);
            ''', [organizer_id, event_type, username, user_email]
        )
    # Make no changes if the organizer already exists

    # Insert event information into the events table 
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
    Updates the event record with the pathname of the event image.
    Used for adding or updating an image for an event.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        ''' 
        update eventcreated set spam = %s where eventid = %s;
        ''', [pathname, event_id]
    )
    conn.commit()

######### helpers related to following orgs ######### 
def get_usertype(conn, userid):
    '''
    Retrieves the user type (e.g., personal, organization) by user ID.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        select usertype from account where userid = %s
        ''', [userid])
    return curs.fetchone()

def follow(conn, userid, orgid):
    '''
    Allows a user to follow an organization.
    Adds a record to the person_interest table.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''insert into person_interest (follower, followed) values (%s, %s);
        ''', [userid, orgid]
    )
    conn.commit()

def unfollow(conn, userid, orgid):
    '''
    Allows a user to unfollow an organization.
    Removes the corresponding record from the person_interest table.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        delete from person_interest
        where follower = %s and followed = %s
        """, [userid, orgid]
    )
    conn.commit()

def is_following(conn, follower, followed):
    '''
    Checks if a user (follower) is following a specific organization (followed).
    Returns True if following, False otherwise.
    '''
    curs = dbi.cursor(conn)
    curs.execute('''SELECT COUNT(*) FROM person_interest
                    WHERE follower = %s AND followed = %s''',
                 [follower, followed])
    count = curs.fetchone()[0]
    return count > 0

def search_orgs_by_keyword(conn, search_term):
    '''
    Retrieves a list of organizations that match a given search term.
    Used for searching organizations by name.
    '''
    curs = dbi.dict_cursor(conn)
    query = '''select org_account.userid, account.username
            from org_account inner join account on org_account.userid = account.userid
            where account.username like %s;'''
    
    curs.execute(query, ('%' + search_term + '%',))
    return curs.fetchall()

########  helpers related to filtering and searching ######### 
def get_filtered_events(conn, filters,userid):
    '''
    Retrieves events matching certain filters such as date, type, tags, and followed organizations.
    Used for filtering events on the homepage or other event listing pages.
    '''
    curs = dbi.dict_cursor(conn)

    # Initilize list of parameters to replace %s
    if userid is None:
        query = '''
        select eventcreated.eventid, eventcreated.organizerid, eventcreated.eventname, eventcreated.eventtype, eventcreated.shortdesc,
            eventcreated.eventdate, eventcreated.starttime, eventcreated.endtime, eventcreated.eventloc, eventcreated.rsvp, eventcreated.eventtag, 
            eventcreated.fulldesc, eventcreated.contactemail, eventcreated.spam, eventcreated.numattendee, account.userid as userid, 
            account.usertype, account.username, account.email
        from eventcreated, account, registration
        where 1=1 and eventcreated.organizerid = account.userid
        '''
        parameters = []
    else: 
        query = '''
        select eventcreated.eventid, eventcreated.organizerid, eventcreated.eventname, eventcreated.eventtype, eventcreated.shortdesc,
            eventcreated.eventdate, eventcreated.starttime, eventcreated.endtime, eventcreated.eventloc, eventcreated.rsvp, eventcreated.eventtag, 
            eventcreated.fulldesc, eventcreated.contactemail, eventcreated.spam, eventcreated.numattendee, account.userid as userid, 
            account.usertype, account.username, account.email, IF(%s IN (SELECT participant FROM registration WHERE eventid = eventcreated.eventid), 'yes', 'no') AS user_rsvped
            from eventcreated, account, registration
            where 1=1 and eventcreated.organizerid = account.userid
        '''
        parameters = [userid]


    # First checks if the user used a date/type/tag/org_name filter at all
    # If not, do not want it in the query
    if filters.get('date'):
        query += ' and eventdate = %s'
        parameters.append(filters['date']) #get user input 

    if filters.get('type'): 
        query += ' and eventtype = %s'
        parameters.append(filters['type'])

    if filters.get('org_name'):
        # The event table does not have a column called org_name, it only has organizerid
        # Checks if the org_name matches the username in the account table, then select events 
        # with a matching organizerid
        query += ' and organizerid in (select userid from account where username LIKE %s)'
        parameters.append('%{}%'.format(filters['org_name']))

    tags_to_filter = filters.get('tags') #this is a list of tags inputted by the user
    if tags_to_filter: 
        # Note: if the user selects career and academic as their tags, 
        # We assume that that the user wants to see events with the career tag or the academic tag
        # (not events with the the career tag and the academic tag simultaneously)
        tag_conditions = []

        # For each tag in the list, want to check if the eventtag colum contains that tag
        for tag in tags_to_filter: 
            tag_conditions.append("eventtag like %s")
            parameters.append('%{}%'.format(tag))
        
        # Assemble the final string 
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
    Retrieves all events whose names match a given search term.
    Includes RSVP information if a user ID is provided.
    Used for searching events by name.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(''' 
        SELECT ec.eventid, ec.organizerid, ec.eventname, ec.eventtype, ec.shortdesc,
        ec.eventdate, ec.starttime, ec.endtime, ec.eventloc, ec.rsvp, ec.eventtag, ec.fulldesc,
        ec.contactemail, ec.spam, ec.numattendee, acc.userid as userid, acc.usertype, 
        acc.username, acc.email, 
            IF(%s IN (SELECT participant FROM registration WHERE eventid = ec.eventid), 'yes', 'no') AS user_rsvped
        FROM eventcreated ec
        JOIN account acc ON ec.organizerid = acc.userid
        LEFT JOIN registration reg ON ec.eventid = reg.eventid AND reg.participant = %s
        WHERE ec.eventname like %s
        GROUP BY ec.eventid
        ORDER BY ec.eventdate, ec.starttime;''', [userid, userid, '%' + search_term + '%'])
    events = curs.fetchall()
    for event in events:
        event = formate_date(event)
    return events

#########  helpers related to updating an event ######### 
def update_event(conn, formData, eventID,userid):
    """
    Updates an event with information gathered from a form.
    Returns the full updated event dictionary.
    Used for modifying event details.
    """
    curs = dbi.dict_cursor(conn)
    
    # Update an event with new data
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
    eventDict = get_event_by_id(conn,eventID,userid)
    return eventDict

def get_followed_orgs(conn, userid): 
    '''
    Retrieves a list of organizations that a personal account is following.
    Used for displaying followed organizations on a user's profile.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''select org_account.userid, account.username
            from org_account inner join person_interest on person_interest.followed = org_account.userid
            inner join account on org_account.userid = account.userid
            where person_interest.follower = %s;''', [userid])
    return curs.fetchall()

def get_account_info(conn, userID):
    """
    Retrieves basic account information for a given user ID.
    Includes user ID, username, user type, email, and profile picture.
    Excludes sensitive information like hashed passwords.
    """
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        SELECT userid, username, usertype, email, profile_pic FROM account
        WHERE userid = %s;
        """, [userID]
    )
    return curs.fetchone()

def update_profile_picture(conn, user_id, picture_path):
    """
    Updates the profile picture path for a user.
    Used for changing a user's profile picture.
    """
    
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        UPDATE account
        SET profile_pic = %s
        WHERE userid = %s;
    ''', [picture_path, user_id])
    conn.commit()

def get_profile_picture(conn, user_id):
    """
    Retrieves the profile picture path for a user.
    Used for displaying a user's profile picture.
    """
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT profile_pic
        FROM account
        WHERE userid = %s;
    ''', [user_id])
    return curs.fetchone()

def delete_event(conn, eventID):
    """
    Removes an event with a given ID from the database.
    Used for deleting events.
    """
    curs = dbi.dict_cursor(conn)
    curs.execute(
        """
        delete from eventcreated
        where eventid = %s;
        """, [eventID]
    )
    conn.commit() # Makes the deletion permanent

######### helpers related to rsvping ######### 
def rsvp_required(conn, event_id):
    '''
    Checks if RSVP is required for a specific event.
    Returns the RSVP requirement status.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''select rsvp from eventcreated where eventid = %s
        ''', [event_id]
    )
    return curs.fetchone()

def user_rsvp_status(conn, event_id, user_id):
    '''
    Checks if a user has RSVPed to a specific event.
    Returns the RSVP record if it exists.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''
        select eventid from registration where eventid = %s and participant = %s;
        ''', [event_id, user_id]
    )
    return curs.fetchone() 

def count_numattendee(conn, event_id):
    '''
    Counts the number of attendees for a specific event.
    Used after a user RSVPs to update the attendee count.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''select count(participant) from registration where eventid = %s''', [event_id]
    )
    count = curs.fetchone()
    count = int(count.get('count(participant)'))
    return count

def rsvp(conn, event_id, user_id):
    '''
    Adds an RSVP record for a user to an event.
    Used when a user RSVPs to an event.
    '''
    
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''insert into registration (eventid, participant) values (%s, %s);
        ''', [event_id, user_id]
    )
    conn.commit()

def cancel_rsvp(conn, event_id, user_id):
    '''
    Deletes an RSVP record for a user from an event.
    Used when a user cancels their RSVP.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute('delete from registration where eventid= %s and participant = %s;', [event_id, user_id])
    conn.commit()
    return "RSVP cancelled"

def update_numattendee(conn,eventid,count):
    '''
    Updates the number of attendees for an event.
    Used after a user RSVPs or cancels their RSVP.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute(
        '''update eventcreated set numattendee = %s where eventid = %s;''',[count,eventid]
    )
    conn.commit()
    return 'updated number of attendees'

def is_valid_filename(filename):
    '''
    Validates the format of a filename.
    Ensures the filename follows a specific pattern (e.g., uploads/10_1700612634.png).
    '''
    # Filename pattern needs to match something like uploads/10_1700612634.png (id_timestamp.extension)
    parts = filename.split('_') 
    potential_uid = parts[0].split('/')[1]
    potential_timestamp = parts[1].split('.')[0]

    # Check if the filename has at least two parts
    if len(parts) != 2:
        return False
    # Check if the first and second parts are numbers
    if not (potential_uid.isdigit() and potential_uid.isdigit()): 
        return False
    return True 

def get_rsvp_info(conn, event_id):
    '''
    Retrieves RSVP information for an event, including user details of attendees.
    '''
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
    Updates account information based on form data.
    Handles updates for both personal and organization accounts.
    Returns the updated account information.
    """
    curs = dbi.dict_cursor(conn)
    username = formData.get('username')
    email = formData.get('email')
    profile_pic = formData.get('profile_pic')

    # Update username and email if provided
    if username or email:
        if get_account_info(conn, userID).get('usertype') == 'personal':
            curs.execute(
                """
                UPDATE account
                SET username = COALESCE(%s, username), email = COALESCE(%s, email)
                WHERE userid = %s;
                """, [username, email, userID]
            )
        else:  # The usertype is 'org'
            eboard = formData.get('eboard')
            org_info = formData.get('org_info')
            curs.execute(
                """
                UPDATE account
                SET username = COALESCE(%s, username), email = COALESCE(%s, email)
                WHERE userid = %s;
                """, [username, email, userID]
            )
            curs.execute(
                """
                UPDATE org_account
                SET eboard = %s, orginfo = %s
                WHERE userid = %s;
                """, [eboard, org_info, userID]
            )

    conn.commit()
    accountDict = get_account_info(conn, userID)
    return accountDict


def update_password(conn, passwd, userID):
    """
    Updates the password for a user account.
    Hashes the new password before storing it in the database.
    """
    curs = dbi.dict_cursor(conn)
    hashed = bcrypt.hashpw(passwd.encode('utf-8'),
                           bcrypt.gensalt())
    
    # Update an account with new data
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
    '''
    Inserts a new question into the QA table for a specific event.
    Parameters include the event ID, user ID of the questioner, and the question content.
    The question date is automatically set to the current time.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        INSERT INTO QA (eventid, userid, question, questionDate)
        VALUES (%s, %s, %s, NOW());
    ''', [event_id, user_id, question_content])
    conn.commit()

def get_qa(conn,event_id):
    '''
    Retrieves all questions and answers for a specific event.
    Includes user information for each question.
    Parameters include the event ID.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        select QA.QAID, QA.eventid, QA.userid, QA.question, QA.answer, QA.questionDate, QA.answerDate,
        account.userid , account.username, account.email, account.profile_pic from QA, account where eventid = %s and QA.userid = account.userid;
    ''', [event_id])
    return curs.fetchall()

def insert_answer(conn, qa_id, organization_id, answer_content):
    '''
    Updates a question in the QA table with an answer from an organization.
    Parameters include the QA ID, organization ID, and the answer content.
    The answer date is automatically set to the current time.
    '''
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        UPDATE QA
        SET orgid = %s, answer = %s, answerDate = NOW()
        WHERE QAID = %s;
    ''', [organization_id, answer_content, qa_id])
    conn.commit()


if __name__ == '__main__':
    database = 'weevent_db' #team db
    #database = os.getlogin() + '_db'
    dbi.conf(database)
    conn = dbi.connect()
