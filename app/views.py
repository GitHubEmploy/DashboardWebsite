# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

# Python modules
import fnmatch
import os, logging

# Flask modules
import threading

import requests
from flask import render_template, request, url_for, redirect, send_from_directory, session, Response, flash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.exceptions import HTTPException, NotFound, abort
import alpaca_trade_api as tradeapi
import datetime
import random
from datetime import date
from dateutil.relativedelta import relativedelta
# App modules
import pandas as pd
from yahoo_fin.stock_info import get_data
from yahoo_fin.stock_info import get_day_gainers
import sys
import trace
from app import app, lm, db, bc
from app.models import User
from app.forms import LoginForm, RegisterForm

from StratusDashboard.app.forms import APIForm

userlist = {}

def findtopstock():
    url = 'https://finance.yahoo.com/screener/predefined/most_actives'
    read = pd.read_html(url)[0]
    symbols = read['Symbol'][0]
    change = read['% Change'][0]
    return symbols, change
def findgainer():
    url = 'https://finance.yahoo.com/gainers'
    read = pd.read_html(url)[0]
    symbols = read['Symbol']
    change = read['% Change']
    price = read['Price (Intraday)']
    return symbols, change, price
def findReplace(directory, find, replace, filePattern):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, filePattern):
            filepath = os.path.join(path, filename)
            with open(filepath) as f:
                s = f.read()
                s = s.replace(find, replace)
                with open(filepath, "w") as f:
                    f.write(s)
                    f.close()

def human_format(num):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # add more suffixes if you need them
    return '%.2f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])

lfcount = 0

def replace(apikey, apisecret, apiurl):
    api = tradeapi.REST(apikey, apisecret, apiurl)
    one_month = date.today() + relativedelta(hours=-5)
    indexreturn = ''
    resstock = ''
    daygraph = []
    jsquery = ''
    ccount = 0
    numblist = []
    topstocklist = []
    openpositions = []
    domain = 'StratusDashboard.githubemploy.repl.co'
    account = api.get_account()
    gainer, gainerchange, gainerprice = findgainer()

    lastMonth = (datetime.date.today().replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    lastdate = api.get_portfolio_history(date_start=lastMonth, date_end=datetime.date.today(), period=None,
                                         timeframe='15Min')
    dayrundict = api.get_portfolio_history(date_start=str(str(datetime.date.today()).split('-')[0]) + '-' + str(str(datetime.date.today()).split('-')[1]) + '-' + str(int(str(datetime.date.today()).split('-')[2])-1), date_end=datetime.date.today(), period=None, timeframe='15Min').df.to_dict()['equity'].values()
    balance_change = str(round(float(account.equity) - float(account.last_equity), 2))
    print(balance_change)
    topstock, stockchange = findtopstock()
    topstockdata = get_data(topstock, start_date = str(one_month), end_date = datetime.date.today(), index_as_date = True, interval = "1d").to_dict()['open'].values()

    for item in topstockdata:
        topstocklist.append(item)
    for loop in range(0, 6, 1):
        numblist.append(str(random.randint(0,18)))
    with open('/Users/mohit/PycharmProjects/SerpentAI/StratusDashboard/app/templates/pages/index.html', 'r') as reader:
        for line in reader:
            indexreturn = indexreturn + line
    with open('/Users/mohit/PycharmProjects/SerpentAI/StratusDashboard/app/static/assets/js/argon.js', 'r') as reader:
        for line in reader:
            jsquery = jsquery + line
    with open('/Users/mohit/PycharmProjects/SerpentAI/StratusDashboard/app/static/assets/js/argon.js', 'w+') as reader:
        jsquery = jsquery.replace('[0, 20, 10, 30, 15, 40, 20, 60, 60]', str(numblist))
        reader.write(jsquery)
    with open('/Users/mohit/PycharmProjects/SerpentAI/StratusDashboard/app/templates/newpages/index.html', 'w+') as writer:
        if float(account.buying_power) <= float(list(lastdate.df.to_dict()['equity'].values())[0]):
            resacc = "fas fa-arrow-down"
            accolor = 'text-danger mr-2'
        if float(account.buying_power) > float(list(lastdate.df.to_dict()['equity'].values())[0]):
            resacc = "fa fa-arrow-up"
            accolor = 'text-success mr-2'
        if str(''.join([i for i in stockchange if not i.isdigit()])).strip().replace('.', '').replace('%', '') == '-':
            resstock = "fas fa-arrow-down"
            stockcolor = 'text-danger mr-2'
        if str(''.join([i for i in stockchange if not i.isdigit()])).strip().replace('.', '').replace('%', '') == '+':
            resstock = "fa fa-arrow-up"
            stockcolor = 'text-success mr-2'
        stockchange = str(stockchange).replace('+', '').replace('-', '')
        portfolio = api.list_positions()
        # Print the quantity of shares for each position.
        for position in portfolio:
            openpositions.append(str(position.symbol))

        sendvar = str(indexreturn).replace('REPLACEACCOUNTVALUE', str(account.buying_power) + '$').replace('ACCARROW', resacc).replace('ACCPERCENT', str(human_format(abs(float(account.buying_power) - float(list(lastdate.df.to_dict()['equity'].values())[0]))))).replace('PROFITLOSS', str(balance_change)).replace('REPLACESTOCK', topstock).replace('REPLACECHANGE', str(stockchange)).replace('RESSTOCK', resstock).replace('TEXTSTOCK', stockcolor).replace('ACCOLOR', accolor).replace('OPENPOSITIONS', str(len(openpositions))+' Stock(s)')
        sendvar = sendvar.replace('REPLACEDAILYDATA', str(topstocklist))
        for item in api.list_orders(status='closed', limit=5):
            ccount = ccount + 1
            sendvar = sendvar.replace('ITEM'+str(ccount), str(item.symbol))
            sendvar = sendvar.replace('SHARES'+str(ccount), str(item.qty))
            sendvar = sendvar.replace('SIDE'+str(ccount), str(item.side))
            if str(item.side) == 'buy':
                sendvar = sendvar.replace('CLASS'+str(ccount), 'fas fa-arrow-up text-success mr-3')
            else:
                sendvar = sendvar.replace('CLASS'+str(ccount), 'fas fa-arrow-down text-warning mr-3')
            sendvar = sendvar.replace('TYPE'+str(ccount), str(item.time_in_force))
            #print(item.symbol, item.qty, item.side, item.time_in_force)
        for loop in range(0, 6, 1):
            #print(str(str(gainerchange[loop]).replace('%', '').replace('+', '').replace('-', '').strip()))
            sendvar = sendvar.replace('GAINPRICE'+str(loop), str(gainerprice[loop])+'$')
            sendvar = sendvar.replace('GAINSTOCK'+str(loop), gainer[loop])
            sendvar = sendvar.replace('GAINPERCENT'+str(loop), str(str(gainerchange[loop]).replace('%', '').replace('+', '').replace('-', '').strip()))
        sendvar = sendvar.replace('DOMAINPORT', domain).replace('APIKEY', apikey).replace('APISECRET', apisecret).replace('APIURL', apiurl)
        writer.write(sendvar)

session = {}
@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@app.route('/startform.html', methods=['GET', 'POST'])
def startform():
    form = APIForm(request.form)
    if form.validate() or request.method == "POST":
        session['apikey'] = str(form.pubapi.data)
        session['secretkey'] = str(form.secapi.data)
        session['urlkey'] = str(form.urlapi.data)
        print(form.pubapi.data, form.secapi.data, form.urlapi.data)
        return redirect('/start.html')
    return render_template('layouts/api-default.html', content=render_template('pages/startform.html', form=form))
    #return render_template('pages/startform.html', form=form)

@app.route('/start.html')
def start():
    try:
        apikey = session['apikey']
    except:
        return render_template('layouts/api-default.html', content=render_template('pages/404.html'))
    privatekey = session['secretkey']
    apiurl = session['urlkey']
    usedir = str('user' + apikey)
    isDirectory = os.path.isdir(usedir)
    runyn = True
    def runuser():
        os.system('cd ' + usedir + ' && python RunFile.py')
    if isDirectory == True:
        userlist[apikey] = threading.Thread(target=runuser)
        userlist[apikey].start()
    elif isDirectory == False:
        replace(str(apikey), str(privatekey), str(apiurl))
        os.system('git clone https://github.com/GitHubEmploy/SuperSimpleAITrading.git '+usedir)
        findReplace(str(str('user') + str(apikey)), "publicapikey", apikey, "*.csv")
        findReplace(str(str('user') + str(apikey)), "secretapikey", privatekey, "*.csv")
        findReplace(str(str('user') + str(apikey)), "usageurl", apiurl, "*.csv")

        userlist[apikey] = threading.Thread(target=runuser)
        userlist[apikey].start()
    return render_template('layouts/api-default.html', content=render_template('pages/startedproc.html'))
# Logout user
@app.route('/logout.html')
def logout():
    logout_user()
    form = LoginForm(request.form)
    return redirect("/login.html")


# Register a new user
@app.route('/register.html', methods=['GET', 'POST'])
def register():
    # declare the Registration Form
    form = RegisterForm(request.form)

    msg = None

    if request.method == 'GET':
        return render_template('layouts/auth-default.html',
                               content=render_template('pages/register.html', form=form, msg=msg))

    # check if both http method is POST and form is valid on submit
    if form.validate_on_submit():

        # assign form data to variables
        username = request.form.get('username', '', type=str)
        password = request.form.get('password', '', type=str)
        email = request.form.get('email', '', type=str)

        # filter User out of database through username
        user = User.query.filter_by(user=username).first()

        # filter User out of database through username
        user_by_email = User.query.filter_by(email=email).first()

        if user or user_by_email:
            msg = 'Error: User exists!'

        else:

            pw_hash = password  # bc.generate_password_hash(password)

            user = User(username, email, pw_hash)

            user.save()

            msg = 'User created, please <a href="' + url_for('login') + '">login</a>'

    else:
        msg = 'Input error'

    return render_template('layouts/auth-default.html',
                           content=render_template('pages/register.html', form=form, msg=msg))

# Authenticate user
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    # Declare the login form
    form = LoginForm(request.form)

    # Flask message injected into the page, in case of any errors
    msg = None

    # check if both http method is POST and form is valid on submit
    if form.validate_on_submit():

        # assign form data to variables
        username = request.form.get('username', '', type=str)
        password = request.form.get('password', '', type=str)

        # filter User out of database through username
        user = User.query.filter_by(user=username).first()

        if user:

            # if bc.check_password_hash(user.password, password):
            if user.password == password:
                login_user(user)
                return redirect('/')
            else:
                msg = "Wrong password. Please try again."
        else:
            msg = "Unkown user"

    return render_template('layouts/auth-default.html',
                           content=render_template('pages/login.html', form=form, msg=msg))

@app.route('/status.html', methods=['GET', 'POST'])
def statusapi():
    apikey = session['apikey']
    try:
        userlist[apikey].isAlive()
        return render_template('layouts/api-default.html', content=render_template('pages/apialive.html'))
    except:
        try:
            return render_template('layouts/api-default.html', content=render_template('pages/apinotalive.html'))
        except:
            return render_template('layouts/api-default.html', content=render_template('pages/404.html'))
@app.route('/stop.html', methods=['GET', 'POST'])
def stopapi():
    apikey = session['apikey']
    runyn = False
    return render_template('layouts/api-default.html', content=render_template('pages/stopapi.html'))
    #return 'Stopping Process Gracefully, this may take up to 10 minutes. Please be patient.'
@app.route('/', methods=['GET', 'POST'])
def default():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    form = APIForm(request.form)
    if form.validate() or request.method == "POST":
        try:
            session['apikey'] = str(form.pubapi.data)
            session['secretkey'] = str(form.secapi.data)
            session['urlkey'] = str(form.urlapi.data)
            replace(str(form.pubapi.data), str(form.secapi.data), str(form.urlapi.data))
        except:
            return render_template('layouts/api-default.html', content=render_template('pages/invalidapi.html', form=form, msg='Invalid API Keys/Combination. Visit https://alpaca.markets to get your API Keys!'))
        #print(form.pubapi.data, form.secapi.data, form.urlapi.data)
        return render_template('layouts/default.html', content=render_template('newpages/index.html'))
    return render_template('layouts/api-default.html', content=render_template('pages/startform.html', form=form))

    # print(str(indexreturn).replace('REPLACESERVERSTATUS', str(account.buying_power)))


@app.route('/<path>')
def index(path):
    return render_template('layouts/auth-default.html',
                            content=render_template( 'pages/404.html' ) )


# Return sitemap
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'sitemap.xml')
