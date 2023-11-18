from flask import (Flask, render_template, make_response, url_for, request,
                   redirect, flash, session, send_from_directory, jsonify)
from werkzeug.utils import secure_filename
from datetime import datetime
app = Flask(__name__)

import cs304dbi as dbi

import random, os, helpers_nov18

app.secret_key = 'your secret here'
# replace that with a random key
app.secret_key = ''.join([ random.choice(('ABCDEFGHIJKLMNOPQRSTUVXYZ' +
                                          'abcdefghijklmnopqrstuvxyz' +
                                          '0123456789'))
                           for i in range(20) ])

# This gets us better error messages for certain common request errors
app.config['TRAP_BAD_REQUEST_ERRORS'] = True

@app.route('/')
def index():
    return render_template('main.html',title='Hello')


@app.route('/create_event/', methods = ['GET', 'POST'])
def create_event():
    '''
    This handler function is for creating an event (event information collection
    and data insertion into tables)
    '''
    conn = dbi.connect()
    if request.method == "GET":
        return render_template("create_event.html", method="POST")

    else:
        #note: since we're not enforcing login at this phase, we need to collect this information
        #so that the account table can be populated (if it is not populationed, we will get referential)
        #integrity issues) when we insert event information
        #after we enforce login, we no longer need to collect organizer_id, username, and user_email
        organizer_id = request.form.get("organizer_id")
        username = request.form.get("username")
        user_email = request.form.get("user_email")


        #we will always need the below information
        event_name = request.form.get("event_name")
        event_type = request.form.get("event_type")
        short_description = request.form.get("short_desc")
        event_date = request.form.get("event_date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        event_location = request.form.get("event_location")
        rsvp = request.form.get("rsvp_required")
        full_description= request.form.get("full_desc")
        contact_email = request.form.get("contact_email")
        spam = request.form.get("spam")
        
        #get the tags as a list
        #but when we insert this field into the table, we want it as a string with each tag 
        #separated by a comma (e.g., "academic,sport,cultural")
        event_tags_list = request.form.getlist("event_tags")
        if event_tags_list: 
            event_tags = ','.join(event_tags_list)
        else: 
            event_tags = None

        #????????? I'm a little confused by why we need the flag and flashing here, 
        #if we enforce that a field is required, the form cannot be submitted if it's just an empty string
        # flag = False
        # # if missing event name 
        # if event_name == "":
        #     flash("Please enter event name")
        #     flag = True

        # # if missing event type 
        # if event_type == "":
        #     flash("Please enter event type")
        #     flag = True
        
        # # if missing short description 
        # if short_description == "":
        #     flash("Please enter short description")
        #     flag = True

        # # if missing start time
        # if start_time == "":
        #     flash("Please enter start time")
        #     flag = True

        # # if missing end time
        # if end_time == "":
        #     flash("Please enter end time")
        #     flag = True

        # # if missing event location 
        # if event_location == "":
        #     flash("Please enter event location")
        #     flag = True
        
        # # if missing rsvp information 
        # if rsvp == "":
        #     flash("Please enter rsvp information")
        #     flag = True

        # # if missing full_description 
        # if full_description == "":
        #     flash("Please enter full description")
        #     flag = True

        # # if missing contact email 
        # if contact_email == "":
        #     flash("Please enter contact email")
        #     flag = True

        # # if user enter all required inputs
        # if flag == False:


        #*********I changed the parameter passing here because I previously had to modify the tags input
        helpers_nov18.insert_event_data(conn, organizer_id, username, 
                                    user_email, event_name, event_type, 
                                    hort_description, event_date, start_time, 
                                    end_time, event_location, rsvp, event_tags, 
                                    full_description, contact_email, spam)
        #ret = helpers.insert_event_data(conn,request.form)
        flash("Event successfully created.")
        return redirect(url_for("create_event"))


@app.route('/all_events/')
def all_events():
    '''
    Renders a page that lists all events in the database, by name
    Mainly just for testing purposes
    '''
    conn = dbi.connect()
    all_events = helpers_nov18.get_all_events(conn)
    return render_template('all_events.html', 
            page_title='All Events', 
            data = all_events)

@app.route('/see_events/', methods=['GET', 'POST'])
def see_events():
    '''
    This handler function renders a page that displays all events 
    or certain events matching a filter
    '''
    if request.method == 'POST':
        #get all the filters applied by the user and store in a dictionary
        #rationale: one may want to filter by tags and date  
        filters = {
            'date': request.form.get('date'), 
            'type': request.form.get('type'), 
            'org_name': request.form.get('org_name'),
            'tags': request.form.getlist('event_tags')
        }
        conn = dbi.connect()

        #fetch the events that match the filters via a helper function
        events = helpers_nov18.get_filtered_events(conn, filters)
            
    else:
        #if get request, load all events
        conn = dbi.connect()
        events = helpers_nov18.get_all_events(conn)
        #replace with jiayi's helper function

    return render_template('Homepage.html', events=events) 
    #replace the second part of the html code with jiayi's html

@app.route('/search_events/', methods=['GET', 'POST'])
def search_events():
    '''
    This handler function renders a page where the user can search events by their names
    '''
    if request.method == 'POST':
        search_term = request.form.get('search')
        conn = dbi.connect()

        #fetch events whose eventname contain the search term via a helper function
        events = helpers_nov18.search_events(conn, search_term)

        return render_template('search_events.html', events=events, search_term=search_term)
        #replace event display html with jiayi's code
    else: 
        return render_template('search_events.html')
        #replace event display htmlwith jiayi's code


@app.route('/update/<int:eventID>', methods=['GET','POST'])
def update(eventID):
    '''
    Shows a form for updating a particular event, with the eventID of the event in the URL on GET
    On POST does the update and shows the form again.
    '''
    conn = dbi.connect()

    if request.method == 'POST':
        #if updating the form
        if request.form.get('submit') == 'update': # if updating the form, check values
            #turn list of tags into 1 str for easy passing
            event_tags_list = request.form.getlist("event_tags")
            if event_tags_list: 
                event_tags = ','.join(event_tags_list)
            else: 
                event_tags = 'None'
            eventDictToPass = request.form.to_dict()            
            eventDictToPass['event_tags'] = event_tags

            eventDict = helpers_nov18.update_event(conn, eventDictToPass, eventID)
           
        #if deleting the form
        elif request.form.get('submit') == 'delete': # find event with this ID and delete the event
            eventDict = helpers_nov18.event_details(conn, eventID)
            helpers_nov18.delete_event(conn, eventID)
            flash(f"Event ({eventDict.get('eventname')}) was deleted successfully")
            return redirect(url_for('index'))
        else: #Shouldn't get here
            flash(f"ERROR: neither update or delete")
        #if the POST is a delete, will return a redirect to the home page for now
    elif request.method == 'GET':
    #either way, the return will be an update page for the event
        eventDict = helpers_nov18.event_details(conn, eventID)
        event_tags = eventDict.get("eventtag")
        if eventDict == None: #Shouldn't happen
            flash('Error: eventDict is empty with this eventID')
            return redirect(url_for('index'))
    return render_template('update_event.html', page_title='Fill in Missing Data', eventDict = eventDict, event_tags = event_tags)





@app.route('/greet/', methods=["GET", "POST"])
def greet():
    if request.method == 'GET':
        return render_template('greet.html', title='Customized Greeting')
    else:
        try:
            username = request.form['username'] # throws error if there's trouble
            flash('form submission successful')
            return render_template('greet.html',
                                   title='Welcome '+username,
                                   name=username)

        except Exception as err:
            flash('form submission error'+str(err))
            return redirect( url_for('index') )

@app.route('/formecho/', methods=['GET','POST'])
def formecho():
    if request.method == 'GET':
        return render_template('form_data.html',
                               method=request.method,
                               form_data=request.args)
    elif request.method == 'POST':
        return render_template('form_data.html',
                               method=request.method,
                               form_data=request.form)
    else:
        # maybe PUT?
        return render_template('form_data.html',
                               method=request.method,
                               form_data={})

@app.route('/testform/')
def testform():
    # these forms go to the formecho route
    return render_template('testform.html')


if __name__ == '__main__':
    import sys, os
    if len(sys.argv) > 1:
        # arg, if any, is the desired port number
        port = int(sys.argv[1])
        assert(port>1024)
    else:
        port = os.getuid()
    # set this local variable to 'wmdb' or your personal or team db
    #db_to_use = 'weevent_db' #team db
    #db_to_use = os.getlogin() + '_db' #personal db
    db_to_use = os.getlogin() + '_db'
    print('will connect to {}'.format(db_to_use))
    dbi.conf(db_to_use)
    app.debug = True
    app.run('0.0.0.0',port)
