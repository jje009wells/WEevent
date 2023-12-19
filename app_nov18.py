# @authors: Jen Enriquez, Victoria Lu, Jiayi Wu, Yannis Zhu

from flask import (Flask, render_template, make_response, url_for, request,
                   redirect, flash, session, send_from_directory, jsonify)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

import time
app = Flask(__name__)
from datetime import datetime

import cs304dbi as dbi

import random, os, helpers_nov18, weeventlogin

app.secret_key = 'your secret here'
# replace that with a random key
app.secret_key = ''.join([ random.choice(('ABCDEFGHIJKLMNOPQRSTUVXYZ' +
                                          'abcdefghijklmnopqrstuvxyz' +
                                          '0123456789'))
                           for i in range(20) ])

# new for file upload
app.config['UPLOADS'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 1*1024*1024 # 1 MB

# This gets us better error messages for certain common request errors
app.config['TRAP_BAD_REQUEST_ERRORS'] = True

# so the that the session will expire eventually?
#app.config["SESSION_PERMANENT"] = False

@app.route('/')
def index():
    '''
    Renders the homepage 
    '''
    conn = dbi.connect()
    user_id = session.get('uid')
    events = helpers_nov18.get_homepage_events(conn, user_id=user_id)
    upcoming_events = helpers_nov18.get_upcoming_events(conn,user_id=user_id)
    return render_template('all_events.html', page_title='All Events', events = events, upcoming_events=upcoming_events)

@app.route('/uploads/<filename>/')
def uploads(filename):
    '''
    This handler function sends spam to the browser
    '''
    return send_from_directory(app.config['UPLOADS'], filename) 

@app.route('/create_event/', methods = ['GET', 'POST'])
def create_event():
    '''
    Renders the event creation form and handles data insertion
    '''
    conn = dbi.connect()
    if request.method == "GET":
        if session.get('uid') is None:
            flash("You are not logged in, please log in to create an event!")
            return redirect(url_for('login'))
        else:
            uid = session['uid']
            account_info = helpers_nov18.get_account_info(conn, userID=uid)

            if account_info['usertype'] == 'org':
                # If the user is an organization, hardcode 'type' field to 'org' in the form
                return render_template("create_event.html", page_title='Create Event', method="POST", eventtype='org')
            else:
                # If the user is an individual, hardcode 'type' field to 'personal' in the form
                return render_template("create_event.html", page_title='Create Event', method="POST", eventtype='personal')
    else:
        if session.get('uid') is None:
            flash("You are not logged in, please log in to create an event!")
            return redirect(url_for('login'))
            flash('I get here when its a post')
        else:
            accountInfo = helpers_nov18.get_account_info(conn, userID=session.get('uid'))
            organizer_id = session.get('uid')
            username = session.get('username')
            user_email = accountInfo.get('email')

            #we will always need the below information
            event_name = request.form.get("event_name")
            event_type = accountInfo.get("usertype") # user should not be able to enter this theirself
            short_description = request.form.get("short_desc")
            event_date = request.form.get("event_date")
            start_time = request.form.get("start_time")
            end_time = request.form.get("end_time")
            event_location = request.form.get("event_location")
            rsvp = request.form.get("rsvp_required")
            full_description= request.form.get("full_desc")
            contact_email = user_email # This should probably just be the user's own account email
            #spam = request.form.get("event_image")
            
            #get the tags as a list
            #but when we insert this field into the table, we want it as a string with each tag 
            #separated by a comma (e.g., "academic,sport,cultural")
            event_tags_list = request.form.getlist("event_tags")
            if event_tags_list: 
                event_tags = ','.join(event_tags_list)
            else: 
                event_tags = None
            
            #first insert the event without the spam 
            #helpers_nov18.insert_event_data returns the event_id of the newly inserted event
            event_id = helpers_nov18.insert_event_data(conn, organizer_id, username, 
                                        user_email, event_name, event_type, 
                                        short_description, event_date, start_time, 
                                        end_time, event_location, rsvp, event_tags, 
                                        full_description, contact_email, None)

            #if spam was uploaded, upload it to the uploads folder with a unique name
            f = request.files['event_image']
            if f: 
                try:
                    nm = int(organizer_id) # may throw error
                    user_filename = f.filename
                    ext = user_filename.split('.')[-1]
                    timestamp = int(time.time()) 
                    filename = secure_filename('{}_{}.{}'.format(nm,timestamp,ext))
                    pathname = os.path.join(app.config['UPLOADS'],filename)
                    f.save(pathname)
                    flash('Upload successful')
                except Exception as err:
                    flash('Upload failed {why}'.format(why=err))
                    return render_template('create_event.html', page_title='Create Event')
            else: 
                pathname = None

            #finally, insert the path for the spam
            #want to do this separately at the end so that spam is not uploaded if 
            #an event does not end up being created
            helpers_nov18.insert_event_image(conn, event_id, pathname)
            flash("Event successfully created.") 
            return redirect(url_for("event", event_id = event_id))
            
@app.route('/event/<int:event_id>/')
def event(event_id):
    '''
    Renders the event details page for an event
    '''
    conn = dbi.connect()
    userid = session.get('uid')
    event = helpers_nov18.get_event_by_id(conn, event_id, userid)
    #if the event is valid 
    if event:
        #in case the user directly types in the image in the url, need to check that the filename is legit
        filename = event['spam']
        if filename: 
            valid_filename = helpers_nov18.is_valid_filename(filename)
            if not valid_filename:
                flash("Filename not secure.")
                return redirect(url_for('index'))
            filename = filename.split('/')[-1]
        else:
            filename = None

        rsvp_info = helpers_nov18.get_rsvp_info(conn, event_id) 
        qa = helpers_nov18.get_qa(conn, event_id)
        return render_template('event_detail.html', page_title='Event Details',event=event, filename=filename, rsvp_info = rsvp_info, uid = str(session.get('uid')), qa = qa)

    else:
        flash('Event not found.')
        return redirect(url_for('index'))

@app.route('/profile/<int:profile_user_id>/', methods=['GET'])
@app.route('/profile/', methods=['GET'])
def profile(profile_user_id=None):
    '''
    Renders the profile page based on the user type.
    '''
    conn = dbi.connect()
    current_user_id = session.get('uid')

    # If no specific user ID is provided, use the logged-in user's ID
    if profile_user_id is None:
        profile_user_id = current_user_id

    if profile_user_id is None:
        flash('Please login first.')
        return redirect(url_for('login'))

    usertype = helpers_nov18.get_usertype(conn, profile_user_id)

    if usertype == None:
        flash('User not found.')
        return redirect(url_for('index'))
    
    elif usertype.get('usertype') == 'org':
        # Fetch organization details and render the organization profile template
        org = helpers_nov18.get_org_by_userid(conn, profile_user_id)
        org_event = helpers_nov18.get_events_by_user(conn, profile_user_id, current_user_id)

         # Check if the current user is following the organization
        is_following = False
        if current_user_id:
            is_following = helpers_nov18.is_following(conn, current_user_id, profile_user_id)
        return render_template('org_profile.html',page_title='Org Profile', org=org, org_event=org_event, is_following = is_following)
    
    elif usertype.get('usertype') == 'personal':
        # Fetch personal account details and render the personal user profile template
        # Assuming you have a function to get personal account details
        user = helpers_nov18.get_user_by_userid(conn, profile_user_id)
        events_created = helpers_nov18.get_events_by_user(conn, profile_user_id, current_user_id)
        events_attending = helpers_nov18.get_eventsid_attending(conn,profile_user_id)
        return render_template('user_profile.html', page_title='User Profile', user=user, events_created = events_created, events_attending = events_attending)

@app.route('/follow/<int:followed>/', methods=['POST'])
def follow(followed):
    '''
    Button for user to follow org, only personal users can follow organizations.
    '''
    conn = dbi.connect()
    userid = session.get('uid')
    usertype = helpers_nov18.get_usertype(conn, userid)
    # Check if the user is logged in
    if userid is None:
        flash('Please log in to follow organizations.')
        return redirect(url_for('login'))

    # Check the user type
    usertype = helpers_nov18.get_usertype(conn, userid)
    if usertype is None or usertype.get('usertype') != 'personal':
        flash('Only personal users can follow organizations.')
        return redirect(url_for('index'))
    
    helpers_nov18.follow(conn,userid,followed)
    orgname = helpers_nov18.get_org_by_userid(conn,followed)
    orgname = orgname.get('username')
    flash(f'''You followed {orgname}''')
    return redirect(url_for('profile', profile_user_id = followed))

@app.route('/unfollow/<int:followed>/', methods=['POST'])
def unfollow(followed):
    '''
    Button for user to follow org
    '''
    conn = dbi.connect()
    userid = session.get('uid')
    helpers_nov18.unfollow(conn,userid,followed)
    orgname = helpers_nov18.get_org_by_userid(conn,followed)
    orgname = orgname.get('username')
    flash(f'''You unfollowed {orgname}''')
    return redirect(url_for('profile', profile_user_id = followed))

@app.route('/view_following/<int:profile_userid>/', methods=['GET', 'POST'])
def view_following(profile_userid): 
    '''
    Renders a page that displays the orgs a personal user is following
    and allows the user to search for orgs to follow
    '''
    conn = dbi.connect()
    current_userid = session.get('uid')
    user = helpers_nov18.get_user_by_userid(conn,profile_userid)

    #if user is logged in
    if profile_userid and current_userid: 
        #if a search was made, want to list both the search results and orgs followed
        followed_orgs = helpers_nov18.get_followed_orgs(conn, profile_userid)
        for org in followed_orgs:
            org['is_following'] = helpers_nov18.is_following(conn, current_userid, org['userid'])
        if request.method == 'POST':
            search_term = request.form.get('org_name')
            search_results = helpers_nov18.search_orgs_by_keyword(conn, search_term)
            return render_template('followed_orgs.html', page_title='Followed Orgs', search_results=search_results, followed_orgs=followed_orgs, user= user)
        #if no search was made, just list the orgs followed
        else: 
            return render_template('followed_orgs.html', page_title='Followed Orgs', followed_orgs=followed_orgs, user= user)

    #if user is not logged in, flash a message and redirect to login
    else: 
        flash('Please login first.')
        return redirect(url_for('login'))

@app.route('/filter_events/', methods=['GET', 'POST'])
def filter_events():
    '''
    Renders a page that displays all events or certain events matching a filter
    '''
    userid = session.get('uid')
    if request.method == 'POST':
        #get all the filters applied by the user and store in a dictionary
        #rationale: one may want to filter by tags and date  
        filters = {
            'date': request.form.get('date'), 
            'type': request.form.get('type'), 
            'org_name': request.form.get('org_name'),
            'tags': request.form.getlist('event_tags'),
            'orgs_following': request.form.get('orgs_following'),
            'uid': session.get('uid')
        }
        conn = dbi.connect()

        #fetch the events that match the filters via a helper function
        events = helpers_nov18.get_filtered_events(conn, filters,userid)
        return render_template('all_events.html', page_title='All Events', events=events, filters=filters)
            
    else:
        #if get request, load all events/homepage
        return redirect(url_for('index'))

@app.route('/search_events/', methods=['GET', 'POST'])
def search_events():
    '''
    Renders a page where the user can search events by their names
    '''
    if request.method == 'POST':
        search_term = request.form.get('search')
        conn = dbi.connect()
        userid = session.get('uid')
        #fetch events whose eventname contain the search term via a helper function
        events = helpers_nov18.search_events(conn, search_term,userid=userid)
        return render_template('all_events.html', page_title='All Events', events=events, search_term = search_term)
    
    #if get request, just display all the events
    else: 
        return redirect(url_for('index'))


@app.route('/update/<int:eventID>', methods=['GET','POST'])
def update(eventID):
    '''
    Shows a form for updating a particular event, with the eventID of the event in the URL on GET
    On POST does the update and shows the form again.
    '''
    userid = session.get('uid')
    if userid is None:
        flash("You must be logged in to update an event!")
        return redirect(url_for('login'))
    else:
        conn = dbi.connect()

        if request.method == 'POST':
            #if the user clicked on the update button...
            if request.form.get('submit') == 'update': 

                #convert list of tags into 1 str for easy passing
                event_tags_list = request.form.getlist("event_tags")
                if event_tags_list: 
                    event_tags = ','.join(event_tags_list)
                else: 
                    event_tags = 'None'

                #store all the updated information in one dictionary
                eventDictToPass = request.form.to_dict()            
                eventDictToPass['event_tags'] = event_tags
                print(eventDictToPass)


                # #if user wants to upload a new image, give the newly uploaded file a new filename, 
                # #put it in the uploads folder, and add the new path to the dictionary    
                # f = request.files['event_image']
                # if f: 
                #     try:
                #         nm = int(eventID) # may throw error
                #         user_filename = f.filename
                #         ext = user_filename.split('.')[-1]
                #         timestamp = int(time.time()) 
                #         filename = secure_filename('{}_{}.{}'.format(nm,timestamp,ext))
                #         print(filename)
                #         pathname = os.path.join(app.config['UPLOADS'],filename)
                #         print(pathname)
                #         f.save(pathname)
                #         flash('Upload successful')
                #     except Exception as err:
                #         flash('Upload failed {why}'.format(why=err))
                #         return render_template('create_event.html')
                # else: 
                #     pathname = None
                # eventDictToPass['event_image'] = pathname
            
                eventDict = helpers_nov18.update_event(conn, eventDictToPass, eventID,userid)
                flash(f"Event updated successfully.")
            
            #if the user clicked on the delete button
            elif request.form.get('submit') == 'delete': 
                
                #find event with this ID and delete the event
                eventDict = helpers_nov18.get_event_by_id(conn, eventID, userid)
                helpers_nov18.delete_event(conn, eventID)
                flash(f"Event ({eventDict.get('eventname')}) was deleted successfully")
                return redirect(url_for('index'))
            
            elif request.form.get('submit') == 'update_spam':
                #if user wants to upload a new image, give the newly uploaded file a new filename, 
                #put it in the uploads folder, and add the new path to the dictionary    
                f = request.files['event_image']
                if f: 
                    try:
                        nm = int(eventID) # may throw error
                        user_filename = f.filename
                        ext = user_filename.split('.')[-1]
                        timestamp = int(time.time()) 
                        filename = secure_filename('{}_{}.{}'.format(nm,timestamp,ext))
                        print(filename)
                        pathname = os.path.join(app.config['UPLOADS'],filename)
                        print(pathname)
                        f.save(pathname)
                        flash('Upload successful')
                    except Exception as err:
                        flash('Upload failed {why}'.format(why=err))
                        return render_template('create_event.html', page_title='Create Event')
                else: 
                    pathname = None
                
                eventDict = helpers_nov18.update_event_spam(conn, pathname, eventID,userid)
                print(eventDict)
                event_tags = eventDict.get('eventtag')
                flash(f"Image updated successfully.")

            else: #Shouldn't get here
                flash(f"ERROR: neither update or delete")
            return redirect(url_for('event', event_id = eventID))

            

        #if get request, display the update page for the event
        elif request.method == 'GET':
            eventDict = helpers_nov18.get_event_by_id(conn, eventID, userid)
            event_tags = eventDict.get("eventtag")
            print(eventDict.get('starttime'))

            if eventDict == None: 
                #technically shouldn't happen as user is only shown the option to update events already created, but just to be safe
                flash('Error: eventDict is empty with this eventID')
                return redirect(url_for('index'))
            return render_template('update_event.html', page_title='Fill in Missing Data', eventDict = eventDict, event_tags = event_tags)

@app.route('/register/', methods=['GET', 'POST'])
def register():
    '''
    Shows a form for registering an account with our DB, can choose to submit either the 
    personal account or the org account based on the provided information.
    '''
    if request.method == 'POST':
        # Extract form data
        userInfo = {
            'user_type': request.form['account_type'],
            'username': request.form['username'],
            'email': request.form['email'],
            'password1': request.form['password1'],
            'password2': request.form['password2']
        }

        # Basic validation
        if userInfo['password1'] != userInfo['password2']:
            flash('Passwords do not match.')
            return redirect(url_for('register'))

        # Insert user
        conn = dbi.connect()
        uid, is_dup, other_err = weeventlogin.insert_user(conn, userInfo)

        if other_err:
            raise other_err  # In production, you would handle this more gracefully
        if is_dup:
            flash('That username is already taken.')
            return redirect(url_for('register'))

        # Set user session or any other post-registration steps
        flash('You were successfully registered!')
        session['username'] = userInfo['username']
        session['uid'] = uid
        session['usertype'] = userInfo['user_type']
        # Redirect to profile or another post-registration page
        return redirect(url_for('index'))  # Replace 'index' with your post-registration page

    # For a GET request, just display the registration form
    return render_template('register_account.html', page_title='Register an Account')

@app.route('/login/', methods=['GET','POST'])
def login():
    '''
    Shows a form for registering an account with our DB, can choose to submit either the personal account or the org account
    '''
    #conn = dbi.connect()

    if request.method == 'POST':
        #if the user clicked on the register personal
        if request.form.get('submit') == 'login': 
            # get the info from the personal account form
            username = request.form.get('username')
            passwd = request.form.get('password')
            conn = dbi.connect()
            (ok, uid) = weeventlogin.login_user(conn, username, passwd)
            print("uid is ", uid)
            if not ok:
                flash('login incorrect, please try again or join')
                return redirect(url_for('login'))
            ## success
            print('LOGIN', username)
            flash('successfully logged in as '+username)
            session['username'] = username
            session['uid'] = uid
            usertype = helpers_nov18.get_usertype(conn,uid)
            usertype = usertype.get('usertype')
            session['usertype'] = usertype
            #session['email'] = accountInfo.get('email')
            #session['visits'] = 1 #don't think we need to keep track of this?
            return redirect( url_for('index') )

            
        #if the user clicked on the delete button
        else: #value was not login, shouldn't get here 
            flash(f"login button was not clicked, shouldn't get here?")

    #if get request, display the update page for the event
    elif request.method == 'GET':
        return render_template('login.html', page_title='Login')


# Not sure when best to use this?
@app.route("/logout")
def logout():
    session['username'] = None
    session['uid'] = None
    session['usertype'] = None
    #session['email'] = None
    return redirect(url_for('index'))

@app.route("/rsvp/<int:event_id>", methods=['POST'])
def rsvp(event_id):
    conn = dbi.connect()

    user_id = session.get('uid')
 
    rsvp_required = helpers_nov18.rsvp_required(conn, event_id)['rsvp']

    #registration_status would be None if the user has not rsvped already
    registration_status = helpers_nov18.user_rsvp_status(conn, event_id, user_id) 
    print(registration_status)

    if rsvp_required == 'yes':
        if registration_status is None: 
            helpers_nov18.rsvp(conn, event_id, user_id)
            count = helpers_nov18.count_numattendee(conn,event_id)
            helpers_nov18.update_numattendee(conn,event_id,count)
            flash('RSVP successful')
        else: 
            helpers_nov18.cancel_rsvp(conn, event_id, user_id)
            count = helpers_nov18.count_numattendee(conn,event_id)
            helpers_nov18.update_numattendee(conn,event_id,count)
            flash('RSVP canceled')

    #technically should not get here as the user would not see the button, but just to be safe...
    else:
        flash('RSVP is not required for this event.')
    
    return redirect(url_for('event', event_id=event_id, registration_status=registration_status))


@app.route('/account_management/', methods=['GET','POST'])
def account_management():
    '''
    Shows a form for updating your account
    On POST does the update and shows the form again.
    '''
    if session.get('uid') is None:
        flash("You are not logged in, please log in to update your account info!")
        return redirect(url_for('login'))
    else:
        conn = dbi.connect()
        #make sure they can also get org info!!!
        print('the user type is ', helpers_nov18.get_usertype(conn,session.get('uid')))
        if helpers_nov18.get_usertype(conn,session.get('uid')).get('usertype') == 'org':
            print('I should be getting org userinfo')
            userInfo = helpers_nov18.get_org_by_userid(conn, session.get('uid'))
        else:
            userInfo = helpers_nov18.get_account_info(conn, session.get('uid'))
        if request.method == 'POST':
            if request.form.get('submit') == 'update_pass':
                passwd1 = request.form.get('password1')
                passwd2 = request.form.get('password2')
                if passwd1 != passwd2:
                    flash('passwords do not match')
                    return redirect( url_for('account_management'))
                else:
                    conn = dbi.connect()
                    helpers_nov18.update_password(conn, passwd1, session.get('uid'))
                    flash("Password was updated! Returning to your profile. Please keep track of new password")
                    return redirect( url_for('profile') )
            else:
                formInfo = request.form.to_dict()
                print('form info is', formInfo)

                newAccountDict = helpers_nov18.update_account(conn, formInfo, session.get('uid'))
                print('the newAccountDict, after updating is, ', newAccountDict)
                session['username'] = newAccountDict.get('username')
                flash('Account info updated. Returning to your profile')
                return redirect( url_for('profile') )
        else: # GET method
            print('userInfo, which will be rendered on a GET, is', userInfo)
            return render_template('update_account.html', page_title='Update Your Account', userInfo = userInfo)

@app.route('/ask_question/<int:event_id>', methods=['POST'])
def ask_question(event_id):
    if session.get('uid') is None:
        flash("You must be logged in to ask a question!")
        return redirect(url_for('login'))

    conn = dbi.connect()
    user_id = session.get('uid')
    question_content = request.form.get('question_content')

    # Assuming a function insert_question exists in helpers_nov18
    helpers_nov18.insert_question(conn, event_id, user_id, question_content)
    flash("Your question has been posted.")
    return redirect(url_for('event', event_id=event_id))


@app.route('/answer_question/<int:event_id>/<int:QAID>', methods=['POST'])
def answer_question(event_id, QAID):
    if session.get('uid') is None:
        flash("You must be logged in to answer a question!")
        return redirect(url_for('login'))

    conn = dbi.connect()
    org_id = session.get('uid')
    answer_content = request.form.get('reply_content')

    # Assuming a function insert_answer exists in helpers_nov18
    # and it correctly updates the answer for the given QAID
    helpers_nov18.insert_answer(conn, QAID, org_id, answer_content)
    flash("Your answer has been posted.")
    return redirect(url_for('event', event_id=event_id))

    
if __name__ == '__main__':
    import sys, os
    if len(sys.argv) > 1:
        # arg, if any, is the desired port number
        port = int(sys.argv[1])
        assert(port>1024)
    else:
        port = os.getuid()
    # set this local variable to 'wmdb' or your personal or team db
    db_to_use = 'weevent_db' #team db
    #db_to_use = os.getlogin() + '_db' #personal db
    print('will connect to {}'.format(db_to_use))
    dbi.conf(db_to_use)
    app.debug = True
    app.run('0.0.0.0',port)

