from flask import (Flask, render_template, make_response, url_for, request,
                   redirect, flash, session, send_from_directory, jsonify)
from werkzeug.utils import secure_filename
app = Flask(__name__)

import cs304dbi as dbi

import random

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
    
    if request.method == "GET":
        return render_template("create_event.html", method="POST")

    else:
        event_name = request.form.get("event-name")
        event_type = request.form.get("event-type")
        short_description = request.form.get("short-description")
        start_time = request.form.get("start-time")
        end_time = request.form.get("end-time")
        event_location = request.form.get("event-location")
        rsvp = request.form.get("rsvp")
        event_tag = request.form.get("event-tag")
        full_description= request.form.get("full-description")
        contact_email = request.form.get("contact-email")
        spam = request.form.get("spam")

        flag = False

        # if missing event name 
        if event_name == "":
            flash("Please enter event name")
            flag = True

        # if missing event type 
        if event_type == "":
            flash("Please enter event type")
            flag = True
        
        # if missing short description 
        if short_description == "":
            flash("Please enter short description")
            flag = True

        # if missing start time
        if start_time == "":
            flash("Please enter start time")
            flag = True

        # if missing end time
        if end_time == "":
            flash("Please enter end time")
            flag = True

        # if missing event location 
        if event_location == "":
            flash("Please enter event location")
            flag = True
        
        # if missing rsvp information 
        if rsvp == "":
            flash("Please enter rsvp information")
            flag = True

        # if missing full_description 
        if full_description == "":
            flash("Please enter full description")
            flag = True

        # if missing contact email 
        if contact_email == "":
            flash("Please enter contact email")
            flag = True

        # if user enter all required inputs
        if flag == True:
            return redirect(url_for("create_event"))



# You will probably not need the routes below, but they are here
# just in case. Please delete them if you are not using them

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
    db_to_use = 'weevent_db' 
    print('will connect to {}'.format(db_to_use))
    dbi.conf(db_to_use)
    app.debug = True
    app.run('0.0.0.0',port)
