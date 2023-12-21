import cs304dbi as dbi
import pymysql
import bcrypt

def insert_user(conn, userInfo, verbose=False):
    '''
    Inserts a new user into the database based on the provided user information.
    Parameters:
        conn: Database connection object
        userInfo: Dictionary containing user information
        verbose: Boolean flag for verbose output (default: False)
    Returns:
        uid: User ID of the newly inserted user or False if an error occurred
        is_dup: Boolean indicating if a duplicate key error occurred
        other_err: False if no error, or the exception object if an error occurred
    '''
    hashed = bcrypt.hashpw(userInfo.get('password1').encode('utf-8'),
                           bcrypt.gensalt())
    curs = dbi.cursor(conn)
    try:
        # Insert into the account table
        curs.execute('''INSERT INTO account (usertype, username, email, hashedp, profile_pic) 
                VALUES(%s, %s, %s, %s, %s)''',
             [userInfo.get('user_type'), userInfo.get('username'),
              userInfo.get('email'), hashed.decode('utf-8'), userInfo.get('profile_pic')])
        
        # Get the last insert id
        curs.execute('select last_insert_id()')
        row = curs.fetchone()
        uid = row[0]
        print(f'New user id: {uid}')

        # Insert into the respective table based on user type
        if userInfo.get('user_type') == 'personal':
            curs.execute('''INSERT INTO personal_account (userid) 
                            VALUES(%s)''', [uid])
            print('inserted into personal account table')
        elif userInfo.get('user_type') == 'org':
            curs.execute('''INSERT INTO org_account (userid, eboard, orginfo) 
                            VALUES(%s, %s, %s)''', [uid, userInfo.get('eboard'), userInfo.get('org_info')])
            print('inserted into organization account table')

        # Commit the transaction
        conn.commit()
        return (uid, False, False)
    except pymysql.err.IntegrityError as err:
        details = err.args
        if verbose:
            print('Error inserting user:', details)
        if details[0] == pymysql.constants.ER.DUP_ENTRY:
            if verbose:
                print('Duplicate key for username', userInfo.get('username'))
            return (False, True, False)
        else:
            if verbose:
                print('Some other database error occurred!')
            return (False, False, err)


def login_user(conn, username, password):
    '''
    Attempts to log in a user with the given username and password.
    Parameters:
        conn: Database connection object
        username: Username of the user attempting to log in
        password: Password of the user attempting to log in
    Returns:
        True and the user ID if login is successful, False and False otherwise.
    '''
    curs = dbi.cursor(conn)
    curs.execute('''SELECT userid, hashedp FROM account 
                    WHERE username = %s''',
                 [username])
    row = curs.fetchone()
    if row is None:
        # No such user
        return (False, False)
    uid, hashed = row
    hashed2_bytes = bcrypt.hashpw(password.encode('utf-8'),
                                  hashed.encode('utf-8'))
    hashed2 = hashed2_bytes.decode('utf-8')
    if hashed == hashed2:
        return (True, uid)
    else:
        # Password incorrect
        return (False, False)

def delete_user(conn, id):
    '''
    Deletes a user from the database based on the user ID.
    Parameters:
        conn: Database connection object
        id: User ID of the user to be deleted
    '''
    curs = dbi.cursor(conn)
    curs.execute('''DELETE FROM account WHERE userid = %s''',
                 [id])
    conn.commit()

if __name__ == '__main__':
    conn = dbi.connect()
    userInfo1 = {'username': 'test2', 'email': 'test2@test', 'password1': '12345', 'password2': '12345', 'submit': 'register_personal', 'user_type': 'personal'}
    userInfo2 = {'username': 'Test Org', 'email': 'test3@test', 'password1': '12345', 'password2': '12345', 'submit': 'register_org', 'user_type': 'org', 'eboard':'Bob, Bob', 'org_info':'This is a test org'}
    (uid1, is_dup, other_err) = insert_user(conn, userInfo1)
    if other_err:
        raise other_err
    if is_dup:
        print('Sorry; that username is taken')
    print(uid1)

    (uid2, is_dup, other_err) = insert_user(conn, userInfo2)
    if other_err:
        raise other_err
    if is_dup:
        print('Sorry; that username is taken')
    print(uid2)
    delete_user(conn, uid1)
    delete_user(conn, uid2)
