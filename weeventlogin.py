import cs304dbi as dbi
import pymysql
import bcrypt

#need to fix this to work with our code, will prob pass a dict of all the user info
def insert_user(conn, userInfo, verbose=False):
    '''inserts given username & password into the userpass table.  
Returns three values: the uid, whether there was a duplicate key error, 
and either false or an exception object.
    '''
    hashed = bcrypt.hashpw(userInfo.get('password1').encode('utf-8'),
                           bcrypt.gensalt())
    curs = dbi.cursor(conn)
    try: 
        curs.execute('''INSERT INTO account (usertype, username, email, hashedp) 
                        VALUES(%s, %s, %s, %s)''',
                     [userInfo.get('user_type'), userInfo.get('username'), userInfo.get('email'), hashed.decode('utf-8')])
        
        curs.execute('select last_insert_id()')
        row = curs.fetchone()
        print(row[0])
        if userInfo.get('user_type') == 'personal':
            curs.execute('''INSERT INTO personal_account (userid) 
                        VALUES(%s)''', [row[0]])
            print('inserted into personal')
        elif userInfo.get('user_type') == 'org':
            curs.execute('''INSERT INTO org_account (userid, eboard, orginfo) 
                        VALUES(%s, %s, %s)''', [row[0], userInfo.get('eboard'),userInfo.get('org_info')])
            print('inserted into org')
        conn.commit()
        return (row[0], False, False)
    except pymysql.err.IntegrityError as err:
        details = err.args
        if verbose:
            print('error inserting user',details)
        if details[0] == pymysql.constants.ER.DUP_ENTRY:
            if verbose:
                print('duplicate key for username {}'.format(userInfo.get('username')))
            return (False, True, False)
        else:
            if verbose:
                print('some other error!')
            return (False, False, err)

def login_user(conn, username, password):
    '''tries to log the user in given username & password. 
Returns True if success and returns the uid as the second value.
Otherwise, False, False.'''
    curs = dbi.cursor(conn)
    curs.execute('''SELECT username, hashedp FROM account 
                    WHERE username = %s''',
                 [username])
    row = curs.fetchone()
    if row is None:
        # no such user
        return (False, False)
    uid, hashed = row
    hashed2_bytes = bcrypt.hashpw(password.encode('utf-8'),
                                  hashed.encode('utf-8'))
    hashed2 = hashed2_bytes.decode('utf-8')
    if hashed == hashed2:
        return (True, uid)
    else:
        # password incorrect
        return (False, False)

def delete_user(conn, id):
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
