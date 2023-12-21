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

# Configuration for file uploads
app.config['UPLOADS'] = 'uploads'# Directory for storing uploaded files
app.config['MAX_CONTENT_LENGTH'] = 1*1024*1024  # Maximum file upload size (1 MB)

# This gets us better error messages for certain common request errors
app.config['TRAP_BAD_REQUEST_ERRORS'] = True


@app.route('/')
def index():
    '''
    Renders the homepage.
    Connects to the database to retrieve and display events.
    Differentiates between upcoming and past events for the user.
    '''
    conn = dbi.connect()
    user_id = session.get('uid')
    events = helpers_nov18.get_homepage_events(conn, user_id=user_id)
    upcoming_events = helpers_nov18.get_upcoming_events(events)
    return render_template('all_events.html', page_title='All Events', events = events, upcoming_events=upcoming_events)

@app.route('/uploads/<filename>/')
def uploads(filename):
    '''
    Serves uploaded files to the client.
    The filename parameter specifies the file to be served from the configured upload directory.
    '''
    return send_from_directory(app.config['UPLOADS'], filename) 

@app.route('/create_event/', methods = ['GET', 'POST'])
def create_event():
    '''
    Handles the creation of new events.
    On GET request: Renders the event creation form.
    On POST request: Processes the submitted form data and inserts the new event into the database.
    Differentiates between organization and individual user types for event creation.
    '''
    conn = dbi.connect()
    if request.method == "GET":
        # Check if user is logged in before rendering the event creation form
        if session.get('uid') is None:
            flash("You are not logged in, please log in to create an event!")
            return redirect(url_for('login'))
        else:
            uid = session['uid']
            account_info = helpers_nov18.get_account_info(conn, userID=uid)

            if account_info['usertype'] == 'org':
                # If the user is an organization, hardcode 'type' field to 'org' in the form
                return render_template("create_event.html", page_title='Create Event', eventtype='org')
            else:
                # If the user is an individual, hardcode 'type' field to 'personal' in the form
                return render_template("create_event.html", page_title='Create Event', eventtype='personal')
    else:
        # Process form data for event creation on POST request
        if session.get('uid') is None:
            flash("You are not logged in, please log in to create an event!")
            return redirect(url_for('login'))
        else:
            accountInfo = helpers_nov18.get_account_info(conn, userID=session.get('uid'))
            organizer_id = session.get('uid')
            username = session.get('username')
            user_email = accountInfo.get('email')

            # Extract event details from the form
            # We will always need the below information
            event_name = request.form.get("event_name")
            event_type = accountInfo.get("usertype") # User should not be able to enter this theirself
            short_description = request.form.get("short_desc")
            event_date = request.form.get("event_date")
            start_time = request.form.get("start_time")
            end_time = request.form.get("end_time")
            event_location = request.form.get("event_location")
            rsvp = request.form.get("rsvp_required")
            full_description= request.form.get("full_desc")
            contact_email = user_email # This should probably just be the user's own account email
            
            # Get the tags as a list
            # But when we insert this field into the table, we want it as a string with each tag 
            # Separated by a comma (e.g., "academic,sport,cultural")
            event_tags_list = request.form.getlist("event_tags")
            if event_tags_list: 
                event_tags = ','.join(event_tags_list)
            else: 
                event_tags = None
            
            # First insert the event without the spam 
            # Helpers_nov18.insert_event_data returns the event_id of the newly inserted event
            event_id = helpers_nov18.insert_event_data(conn, organizer_id, username, 
                                        user_email, event_name, event_type, 
                                        short_description, event_date, start_time, 
                                        end_time, event_location, rsvp, event_tags, 
                                        full_description, contact_email, None)

            # If spam was uploaded, upload it to the uploads folder with a unique name
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

            # Finally, insert the path for the spam
            # We want to do this separately at the end so that spam is not uploaded if 
            # an event does not end up being created
            helpers_nov18.insert_event_image(conn, event_id, pathname)
            flash("Event successfully created.") 
            return redirect(url_for("event", event_id = event_id))

@app.route('/clear_filters/', methods=['GET'])
def clear_filters():
    '''
    Clears all applied filters and redirects the user to the homepage.
    This function is useful for resetting the view to its default state without any active filters.
    '''
    return redirect(url_for('index'))

@app.route('/event/<int:event_id>/')
def event(event_id):
    '''
    Renders the event details page for a specific event.
    - Retrieves event details from the database using the event ID.
    - Validates the filename of any associated image to ensure security.
    - Retrieves additional information like RSVP status and Q&A related to the event.
    - Redirects to the homepage with an error message if the event is not found.
    '''
    conn = dbi.connect()
    userid = session.get('uid')
    event = helpers_nov18.get_event_by_id(conn, event_id, userid)
    
    # Check if the event is valid 
    if event:
        # In case the user directly types in the image in the url, need to check that the filename is legit
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
    Renders the profile page for a user.
    - Determines the user type (organization or personal) and renders the appropriate profile template.
    - Handles both specific user profiles and the logged-in user's profile.
    - Redirects to the login page if the user is not logged in.
    - Displays an error message and redirects to the homepage if the user is not found.
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
    
    # Render the appropriate profile template based on user type
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
        user = helpers_nov18.get_user_by_userid(conn, profile_user_id)
        profile_pic_url = helpers_nov18.get_profile_picture(conn, profile_user_id)
        events_created = helpers_nov18.get_events_by_user(conn, profile_user_id, current_user_id)
        events_attending = helpers_nov18.get_eventsid_attending(conn,profile_user_id)
        return render_template('user_profile.html', page_title='User Profile', user=user, profile_pic_url=profile_pic_url, events_created = events_created, events_attending = events_attending)

@app.route('/follow/<int:followed>/', methods=['POST'])
def follow(followed):
    '''
    Allows a personal user to follow an organization.
    - Verifies that the user is logged in and is a personal user.
    - Adds the organization to the user's followed list.
    - Redirects to the login page if the user is not logged in.
    - Displays an error message and redirects if the user is not a personal user.
    '''
    userid = session.get('uid')
    # Check if the user is logged in
    if userid is None:
        flash('Please log in to follow organizations.')
        return redirect(url_for('login'))

    # Check the user type
    conn = dbi.connect()

    usertype = helpers_nov18.get_usertype(conn, userid)
    if usertype is None or usertype.get('usertype') != 'personal':
        flash('Only personal users can follow organizations.')
        return redirect(url_for('index'))
    
    # Add the organization to the user's followed list
    helpers_nov18.follow(conn,userid,followed)
    orgname = helpers_nov18.get_org_by_userid(conn,followed)
    orgname = orgname.get('username')
    flash(f'''You followed {orgname}''')
    return redirect(url_for('profile', profile_user_id = followed))

@app.route('/unfollow/<int:followed>/', methods=['POST'])
def unfollow(followed):
    '''
    Allows a user to unfollow an organization.
    - Verifies that the user is logged in before proceeding.
    - Removes the organization from the user's followed list.
    - Redirects to the login page if the user is not logged in.
    '''
    userid = session.get('uid')
     
    # Check if the user is logged in
    if userid is None:
        flash('Please log in to follow organizations.')
        return redirect(url_for('login'))
    conn = dbi.connect()
    # Remove the organization from the user's followed list
    helpers_nov18.unfollow(conn,userid,followed)
    orgname = helpers_nov18.get_org_by_userid(conn,followed)
    orgname = orgname.get('username')
    flash(f'''You unfollowed {orgname}''')
    return redirect(url_for('profile', profile_user_id = followed))

@app.route('/view_following/<int:profile_userid>/', methods=['GET'])
def view_following(profile_userid):
    '''
    Renders a page displaying the organizations a personal user is following.
    - Allows the user to search for organizations to follow.
    - Displays followed organizations and search results if a search is performed.
    - Redirects to the login page if the user is not logged in.
    '''
    current_userid = session.get('uid')
     
    # Check if the user is logged in
    if current_userid is None:
        flash('Please log in to follow organizations.')
        return redirect(url_for('login'))
    
    conn = dbi.connect()
    user = helpers_nov18.get_user_by_userid(conn, profile_userid)
    org_name = request.args.get('org_name')
    followed_orgs = helpers_nov18.get_followed_orgs(conn, profile_userid)

    # If the search term is provided, perform  search and show both followed orgs and search results
    if org_name:
        search_results = helpers_nov18.search_orgs_by_keyword(conn, org_name)
        return render_template('followed_orgs.html', page_title='Followed Orgs', search_results=search_results, followed_orgs=followed_orgs, user=user)

    # If no search was made, just show the followed orgs
    return render_template('followed_orgs.html', page_title='Followed Orgs', followed_orgs=followed_orgs, user=user)

@app.route('/filter_events/', methods=['GET', 'POST'])
def filter_events():
    '''
    Renders a page that displays events based on applied filters.
    - On POST request: Retrieves filter criteria from the form and fetches matching events.
    - On GET request: Redirects to the homepage to display all events.
    '''
    userid = session.get('uid')
    if request.method == 'POST':
        # Get all the filters applied by the user and store in a dictionary
        # Rationale: one may want to filter by tags and date
        # We want a new dictionary for showing which filters were applied after filtering
        filters = {
            'date': request.form.get('date'), 
            'type': request.form.get('type'), 
            'org_name': request.form.get('org_name'),
            'tags': request.form.getlist('event_tags'),
            'orgs_following': request.form.get('orgs_following'),
            'uid': session.get('uid')
        }
        conn = dbi.connect()

        # Fetch the events that match the filters via a helper function
        events = helpers_nov18.get_filtered_events(conn, filters, userid)
        upcoming_events = helpers_nov18.get_upcoming_events(events)
        return render_template('all_events.html', page_title='All Events', events=events, filters=filters,upcoming_events= upcoming_events)
            
    else:
        # Redirect to homepage for GET request
        return redirect(url_for('index'))

@app.route('/search_events/', methods=['GET'])
def search_events():
    '''
    Renders a page where users can search for events by their names.
    - Fetches events whose names contain the provided search term.
    - Redirects to the homepage if no search term is provided.
    '''
    search_term = request.args.get('search')
    if search_term:
        conn = dbi.connect()
        userid = session.get('uid')
        # Fetch events whose eventname contains the search term via a helper function
        events = helpers_nov18.search_events(conn, search_term, userid=userid)
        upcoming_events = helpers_nov18.get_upcoming_events(events)
        return render_template('all_events.html', page_title='All Events', events=events, search_term=search_term, upcoming_events=upcoming_events)
    else:
        # Redirect to homepage if no search term is provided
        return redirect(url_for('index'))

@app.route('/update/<int:eventID>', methods=['GET','POST'])
def update(eventID):
    '''
    Allows users to update or delete a specific event.
    - On GET request: Shows a form pre-filled with the event's current details.
    - On POST request: Processes the form data to update or delete the event.
    - Redirects to the login page if the user is not logged in.
    '''
    userid = session.get('uid')
    if userid is None:
        # Redirect to login if user is not logged in
        flash("You must be logged in to update an event!")
        return redirect(url_for('login'))
    else:
        conn = dbi.connect()

        if request.method == 'POST':
            # If the user clicked on the update button...
            if request.form.get('submit') == 'update': 

                # Convert list of tags into 1 str for easy passing
                event_tags_list = request.form.getlist("event_tags")
                if event_tags_list: 
                    event_tags = ','.join(event_tags_list)
                else: 
                    event_tags = 'None'

                # Store all the updated information in one dictionary
                eventDictToPass = request.form.to_dict()            
                eventDictToPass['event_tags'] = event_tags
            
                eventDict = helpers_nov18.update_event(conn, eventDictToPass, eventID,userid)
                flash(f"Event updated successfully.")
            
            # If the user clicked on the delete button
            elif request.form.get('submit') == 'delete': 
                
                # Find event with this ID and delete the event
                eventDict = helpers_nov18.get_event_by_id(conn, eventID, userid)
                helpers_nov18.delete_event(conn, eventID)
                flash(f"Event ({eventDict.get('eventname')}) was deleted successfully")
                return redirect(url_for('index'))
            
            elif request.form.get('submit') == 'update_spam':
                # If user wants to upload a new image, give the newly uploaded file a new filename, 
                # put it in the uploads folder, and add the new path to the dictionary    
                f = request.files['event_image']
                if f: 
                    try:
                        nm = int(eventID) 
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
                
                eventDict = helpers_nov18.insert_event_image(conn, eventID, pathname)
                eventDict2 = helpers_nov18.get_event_by_id(conn, eventID, userid)
                flash(f"Image updated successfully.")

            else: # Error message
                flash(f"ERROR: neither update or delete")
            return redirect(url_for('event', event_id = eventID))

        # If get request, display the update page for the event
        elif request.method == 'GET':
            # Display the event update form
            eventDict = helpers_nov18.get_event_by_id(conn, eventID, userid)
            event_tags = eventDict.get("eventtag")

            if eventDict == None: 
                # Error message
                flash('Error: eventDict is empty with this eventID')
                return redirect(url_for('index'))
            return render_template('update_event.html', page_title='Fill in Missing Data', eventDict = eventDict, event_tags = event_tags)

@app.route('/register/', methods=['GET', 'POST'])
def register():
    '''
    Handles the registration of new users, both personal and organization accounts.
    - On POST request: Processes the registration form and creates a new user account.
    - On GET request: Displays the registration form.
    - Performs basic validation and sets a default profile picture.
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

        # Set default profile picture path
        default_profile_pic = 'static/images/Default_profile_image.png'
        userInfo['profile_pic'] = default_profile_pic

        # Insert new user into the database
        conn = dbi.connect()
        uid, is_dup, other_err = weeventlogin.insert_user(conn, userInfo)

        if other_err:
            raise other_err  # In production, you would handle this more gracefully
        if is_dup:
            flash('That username is already taken.')
            return redirect(url_for('register'))

        # Set user session 
        flash('You were successfully registered!')
        session['username'] = userInfo['username']
        session['uid'] = uid
        session['usertype'] = userInfo['user_type']
        session['userProfilePic'] = userInfo['profile_pic']
        # Redirect to profile or another post-registration page
        return redirect(url_for('index'))  

    # For a GET request, just display the registration form
    return render_template('register_account.html', page_title='Register an Account')

@app.route('/login/', methods=['GET','POST'])
def login():
    '''
    Shows a form for registering an account with our DB, can choose to submit either the personal account or the org account
    '''

    if request.method == 'POST':
        # If the user clicked on the register personal
        if request.form.get('submit') == 'login': 
            # Get the info from the personal account form
            username = request.form.get('username')
            passwd = request.form.get('password')
            conn = dbi.connect()
            (ok, uid) = weeventlogin.login_user(conn, username, passwd)
            if not ok:
                flash('login incorrect, please try again or join')
                return redirect(url_for('login'))
       
            flash('successfully logged in as '+username)
            session['username'] = username
            session['uid'] = uid
            usertype = helpers_nov18.get_usertype(conn,uid)
            usertype = usertype.get('usertype')
            session['usertype'] = usertype
            profile_pic = helpers_nov18.get_profile_picture(conn, uid)
            profile_pic = profile_pic.get('profile_pic')
            session['userProfilePic'] = profile_pic
            return redirect( url_for('index') )

            
        # If the user clicked on the delete button
        else: # Value was not login, shouldn't get here 
            flash(f"login button was not clicked, shouldn't get here?")

    # If get request, display the update page for the event
    elif request.method == 'GET':
        return render_template('login.html', page_title='Login')


@app.route("/logout", methods=['POST'])
def logout():
    '''
    Logs out the current user and clears their session.
    Redirects to the homepage after logout.
    '''
    # Clear user session and redirect to homepage
    session['username'] = None
    session['uid'] = None
    session['usertype'] = None
    return redirect(url_for('index'))

@app.route("/rsvp/<int:event_id>", methods=['POST'])
def rsvp(event_id):
    '''
    Handles RSVP actions for an event.
    - Allows users to RSVP or cancel their RSVP for an event, depending on the event's requirements.
    - Redirects to the login page if the user is not logged in.
    - Updates the RSVP status and attendee count for the event.
    '''

    user_id = session.get('uid')
    if user_id is None:
        flash("You must be logged in to update an event!")
        return redirect(url_for('login'))
 
    conn = dbi.connect()
    rsvp_required = helpers_nov18.rsvp_required(conn, event_id)['rsvp']

    # Registration_status would be None if the user has not rsvped already
    registration_status = helpers_nov18.user_rsvp_status(conn, event_id, user_id) 

    if rsvp_required == 'yes':
        # Handle RSVP or cancellation based on current registration status
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

    # Technically should not get here as the user would not see the button, but just to be safe...
    else:
        flash('RSVP is not required for this event.')
    
    return redirect(url_for('event', event_id=event_id, registration_status=registration_status))


@app.route('/account_management/', methods=['GET', 'POST'])
def account_management():
    '''
    Allows users to manage and update their account information.
    - On POST request: Processes updates to the user's account details, including password and profile picture.
    - On GET request: Displays the account management form with current details.
    - Redirects to the login page if the user is not logged in.
    '''
    uid = session.get('uid')
    if uid is None:
        flash("You are not logged in, please log in to update your account info!")
        return redirect(url_for('login'))
    else:
        conn = dbi.connect()
        
        # Fetch user information based on user type
        if helpers_nov18.get_usertype(conn, session.get('uid')).get('usertype') == 'org':
            userInfo = helpers_nov18.get_org_by_userid(conn, session.get('uid'))
        else:
            userInfo = helpers_nov18.get_account_info(conn, session.get('uid'))

        if request.method == 'POST':
            # Handle different types of account updates
            submit_type = request.form.get('submit')
            formInfo = request.form.to_dict()

            # Handle password update
            if submit_type == 'update_pass':
                passwd1 = formInfo.get('password1')
                passwd2 = formInfo.get('password2')
                if passwd1 != passwd2:
                    flash('Passwords do not match')
                    return redirect(url_for('account_management'))
               
                helpers_nov18.update_password(conn, passwd1, session.get('uid'))
                flash("Password was updated! Returning to your profile. Please keep track of new password")
                return redirect(url_for('profile'))

            elif submit_type == 'update_personal' or submit_type == 'update_org':
                # Account update logic for both personal and org accounts
                username = request.form['username']
                email = request.form['email']
                newAccountDict = helpers_nov18.update_account(conn, formInfo, session.get('uid'))
                session['username'] = newAccountDict.get('username')

                flash('Account info updated. Returning to your profile')
                return redirect(url_for('profile'))

            elif submit_type == 'update_profile_pic':
                # Profile picture upload logic
                profile_pic_file = request.files['profile_pic']
                if profile_pic_file and profile_pic_file.filename != '':
                    try:
                        nm = int(uid) 
                        user_filename = profile_pic_file.filename
                        ext = user_filename.split('.')[-1]
                        timestamp = int(time.time()) 
                        filename = secure_filename('{}_{}.{}'.format(nm,timestamp,ext))
                        pathname = os.path.join(app.config['UPLOADS'],filename)
                        profile_pic_file.save(pathname)
                        helpers_nov18.update_profile_picture(conn, session.get('uid'), pathname)
                        session['userProfilePic'] = pathname
                        flash('Profile picture updated. Returning to your profile')
                        return redirect(url_for('profile'))
                    except Exception as err:
                        flash('Upload failed {why}'.format(why=err))
                        return render_template('update_account.html', page_title='Update Your Account', userInfo=userInfo)

    # Display account management form for GET request
    return render_template('update_account.html', page_title='Update Your Account', userInfo=userInfo)

       
@app.route('/ask_question/<int:event_id>', methods=['POST'])
def ask_question(event_id):
    '''
    Allows logged-in users to ask questions on an event's page.
    - Inserts the user's question into the database.
    - Redirects to the login page if the user is not logged in.
    '''
    if session.get('uid') is None:
        flash("You must be logged in to ask a question!")
        return redirect(url_for('login'))

    conn = dbi.connect()
    user_id = session.get('uid')
    question_content = request.form.get('question_content')

    # Insert question into the database
    helpers_nov18.insert_question(conn, event_id, user_id, question_content)
    flash("Your question has been posted.")
    return redirect(url_for('event', event_id=event_id))


@app.route('/answer_question/<int:event_id>/<int:QAID>', methods=['POST'])
def answer_question(event_id, QAID):
    '''
    Allows logged-in users, particularly organizers, to answer questions on an event's page.
    - Inserts the organizer's answer into the database for the specified question (QAID).
    - Redirects to the login page if the user is not logged in.
    - Redirects back to the event page after posting the answer.
    '''
    if session.get('uid') is None:
        flash("You must be logged in to answer a question!")
        return redirect(url_for('login'))

    conn = dbi.connect()
    org_id = session.get('uid')
    answer_content = request.form.get('reply_content')

    # Insert answer into the database for the given QAID
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
    
    db_to_use = 'weevent_db' #team db
    dbi.conf(db_to_use)
    app.debug = True
    app.run('0.0.0.0',port)

