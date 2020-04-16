
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, url_for, flash, session
from flask_login import login_required, current_user
from markupsafe import escape
from werkzeug.security import check_password_hash, generate_password_hash
import sys
import pandas as pd
import json
from sqlalchemy.engine import create_engine
import recomAlg
import numpy as np

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.config.update(
    TESTING=True,
    SECRET_KEY=b'_5#y2L"F4Q8z\n\xec]/'
)

#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@35.243.220.243/proj1part2
#
# For example, if you had username gravano and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://gravano:foobar@35.243.220.243/proj1part2"
#
#DATABASEURI = "postgresql://user:password@35.243.220.243/proj1part2"
# Use the DB credentials you received by e-mail

DB_USER = "xx"
DB_PASSWORD = "xx"
DB_SERVER = "xxx"
DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/proj1part2"

#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
#engine.execute("""CREATE TABLE IF NOT EXISTS test (
#  id serial,
#  name text
#);""")
#engine.execute("""INSERT INTO test(name) VALUES ('th2830'), ('jz3030');""")
#
##====== top games recommendation ======
top_games = recomAlg.get_top_games(engine)


# Recommendataion
# Model 1: Content based
#df = get_game_data(engine)
#cb = content_based(df)
#recomAlg.cb.get_recommendations('DOOM')
# Model 2: collaborative filtering
#recomAlg.get_cc_recommendations(pdf)

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#

# home page
@app.route('/')
def home():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like
  print(request.args)
  return render_template("home.html")

#game index
@app.route('/games')
def game_index():
  if 'user_id' not in session:
    cmd = 'SELECT game_id, app_name FROM games WHERE game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s'
    games_in =[]
    result = g.conn.execute(cmd, tuple(top_games))
    for game in result:
      games_in.append(game)
      # print(games_in, file=sys.stderr)
    return render_template("./games/index.html", games = games_in, title = "index")
  else:
    return render_template("./games/index_recommender.html")

@app.route('/games/recommendations')
def game_recommendation():
  ## model CC
  [userid, gameid, ratingtable]=recomAlg.get_review_data(engine)
  pdf = recomAlg.unpivot(ratingtable)
  [userRecs_df,gameRecs_df]= recomAlg.get_cc_recommendations(pdf)
  ##
  given_user_id = session['user_id']
  user_loc = userid.get_loc(given_user_id)
  topgames= userRecs_df[userRecs_df['user_id'] == user_loc].recommendations
  topgames = topgames.reset_index().recommendations
  pdtopgames =pd.DataFrame(topgames[0], columns = ['games','score'])
  ##
  result_list = pdtopgames.games
  result=[]
  for game in result_list:
      result.append(str(game))
  cmd = 'SELECT game_id, app_name FROM games WHERE game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s or game_id = %s'
  games_in =[]
  result = g.conn.execute(cmd, tuple(result))
  for game in result:
      games_in.append(game)
  return render_template("./games/index_login_user.html", games = games_in)

# search
@app.route('/search',methods=['POST'])
def search():
  if request.method == 'POST':
    search_content = request.form['search_content']
    search_content = '%'+search_content+'%'
    game_results_in = []
    cmd = "SELECT game_id, app_name FROM games WHERE app_name ILIKE %s limit 10"
    search_result = g.conn.execute(cmd, (search_content))
    for game in search_result:
        game_results_in.append(game)
    search_content = search_content[1:-1]
    return render_template("search_result.html", game_results = game_results_in, search_content=search_content)
    return redirect('/')

# sign up
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        game_id = session['game_id']
        #print(game_id, file=sys.stderr)
        rating = []
        
        for i in np.arange(1, 9):
            rating.append(request.form['game'+str(i)])
        error = None
        #print(rating)

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif g.conn.execute("""SELECT user_id FROM users WHERE user_id = %s""", (username,)).fetchone() is not None:
            error = 'User {} is already registered.'.format(username)
        print(error)

        if error is None:
            g.conn.execute("""INSERT INTO users (user_id, playtime_total_forever, playtime_total_2week) VALUES (%s, %s, %s)""",(username,0,0))
        
            cmd1 = 'SELECT user_id FROM users WHERE user_id = %s'
            user_id = g.conn.execute(cmd1, (username,)).fetchone()[0]
            # print(user_id[0], file=sys.stderr)

            cmd2 = 'INSERT INTO reviews(user_id, game_id, help_score) VALUES (%s, %s, %s)'
            for i in np.arange(8):
                print((game_id[i],user_id,rating[i]),file=sys.stderr)
                g.conn.execute(cmd2, (user_id, game_id[i],rating[i]))
            flash('User {} successfully registered.'.format(username),'success')
            return redirect(url_for('login'))
        flash(error,'danger')


    cmd = 'SELECT * FROM games ORDER BY random() LIMIT 8'
    games = g.conn.execute(cmd)
    games_for_rate = []
    game_id = []
    for tmp in games:
        games_for_rate.append(tmp)
        game_id.append(tmp['game_id'])
    session['game_id'] = game_id
    return render_template('register.html', games_for_rate= games_for_rate)

# login
@app.route("/login", methods=['GET', 'POST'])
def login():
    print(session)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        user = g.conn.execute(
            """SELECT * FROM users WHERE user_id = %s""", (username,)
        ).fetchone()
        print(user)
        user_password = 'db'

        if user is None:
            error = 'Incorrect username.'
        elif not user_password == password:
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['user_id']

            return redirect(url_for('game_index'))

        flash(error,'danger')

    return render_template('login.html',title='Login')

# logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('game_index'))

    
if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()
