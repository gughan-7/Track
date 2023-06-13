import base64
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from dateutil import parser
from . import db
from .models import Tracker, User, Log
import datetime
import sqlite3
import matplotlib.pyplot as plt
import io

views = Blueprint('views', __name__)

curuser = 0

@views.route('/login',methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        from .models import User
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in')
                global curuser
                curuser = user
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password')
        else:
            flash('User does not exist.')
    return render_template("login.html", user=curuser)

@views.route('/logout',methods=['GET','POST'])
def logout():
    global curuser
    curuser = 0
    flash('Logged out successfully.')
    return redirect(url_for('views.login'))

@views.route('/signup',methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        firstname = request.form.get('fname')
        lastname = request.form.get('lname')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        from .models import User
        user = User.query.filter_by(email=email).first()
        if user:
            flash('An account has already been created with this email.')
        elif password1 != password2:
            flash('Passwords don\'t match.')
        else:
            from . import db
            new_user = User(firstname=firstname, email=email,  password=generate_password_hash(password1, method='sha256'), lastname=lastname)
            db.session.add(new_user)
            db.session.commit()
            flash('Successfully signed up.')

    return render_template("signup.html", user=curuser)

@views.route('/', methods=['GET', 'POST'])
def home():
    if curuser != 0:
        tracker = Tracker.query.all()
        logs = Log.query.all()
        return render_template("home.html", user=curuser, tracker=tracker,logs=logs)
    else:
        return redirect(url_for('views.login'))


@views.route('/profile', methods=['GET', 'POST'])
def view_profile():
    if curuser != 0:
        use = User.query.get(curuser.id)
        name1 = use.firstname
        last1 = use.lastname
        emai = use.email
        clo = Log.query.filter(Log.user_id == curuser.id).count()
        cto = Tracker.query.filter(Tracker.user_id == curuser.id).count()
        return render_template("profilepage.html", user=curuser,cl=clo,ct=cto, name1=name1,last1=last1,emai=emai)
    else:
        return redirect(url_for('views.login'))

@views.route('/editprofile', methods=['GET','POST'])
def editprofile():
    if curuser != 0:
        use = User.query.get(curuser.id)
        name1 = use.firstname
        last1 = use.lastname
        emai = use.email
        if request.method == 'POST':
            email = request.form.get('email')
            first = request.form.get('fname')
            last = request.form.get('lname')
            curremail = curuser.email
            user = User.query.filter_by(email=email).first()
            if user and curremail != email:
                flash('Account already exists please login.')
            elif len(email) < 6:
                flash('Please enter a valid email address.')
            elif len(first) < 3:
                flash('Please enter a valid first name.')
            else:
                edit = User.query.get(curuser.id)
                edit.firstname = first
                edit.email = email
                edit.lastname = last
                db.session.commit()
                flash('Profile updated.')
            return redirect(url_for('views.view_profile'))
                
        return render_template("editprofile.html",user=curuser,name1=name1,last1=last1,emai=emai)
    else:
        return redirect(url_for('views.login'))

@views.route('/addtracker', methods=['GET','POST'])
def add_tracker():
    if curuser != 0:
        if request.method == 'POST':
            name = request.form.get('name')
            desc = request.form.get('description')
            tlogtype = request.form.get('type')
            sett = request.form.get('settings')
            curuser_id = curuser.id
            tracker = Tracker.query.filter_by(name=name).first()
            if tracker and curuser_id == tracker.user_id:
                flash('Please choose a new name for your tracker')
                return redirect(url_for('views.home'))
            else:
                new_tracker = Tracker(name=name, description=desc, tracker_type=tlogtype, settings=sett, user_id=curuser_id)
                db.session.add(new_tracker)
                db.session.commit()
                flash('Tracker Added')
                return redirect(url_for('views.home'))
        return render_template("addtracker.html", user=curuser)
    else:
        return redirect(url_for('views.login'))

@views.route('/edittracker/<int:tra_id>', methods=['GET','POST'])
def edittracker(tra_id):
    if curuser != 0:
        traker = Tracker.query.get(tra_id)
        if request.method == 'POST':
            name = request.form.get('name')
            desc = request.form.get('description')
            tlogtype = request.form.get('type')
            sett = request.form.get('settings')
            tracker = Tracker.query.filter_by(name=name).first()
            if tracker and curuser.id != tracker.user_id:
                flash('Tracker already exists')
                return redirect(url_for('views.home'))
            else:
                traker.name = name
                traker.description = desc
                traker.trackerlogtype = tlogtype
                traker.settings = sett
                db.session.commit()
                flash('Tracker Updated')
                return redirect(url_for('views.home'))
        return render_template("edittracker.html", user=curuser, tracker=traker)
    else:
        return redirect(url_for('views.login'))

@views.route('/deletetracker/<int:tra_id>', methods=['GET','POST'])
def deletetracker(tra_id):
    if curuser != 0:
        traker = Tracker.query.get(tra_id)
        db.session.delete(traker)
        db.session.commit()
        logs = Log.query.filter(Log.tracker_id == tra_id).all()
        for logg in logs:
            db.session.delete(logg)
        db.session.commit()
        flash("Tracker deleted")
        return redirect(url_for('views.home'))
    else:
        return redirect(url_for('views.login'))

@views.route('/viewtracker/<int:tra_id>', methods=['GET','POST'])
def viewtracker(tra_id):
    if curuser != 0:
        traker = Tracker.query.get(tra_id)
        log = Log.query.all()
        conn = sqlite3.connect(r'website\database.db')
        cur = conn.cursor()
        cur.execute('SELECT timestamp, value FROM Log WHERE user_id={} AND tracker_id={}'.format(curuser.id,traker.id))
        data = cur.fetchall()
        dates = []
        value = []
        for row in data:
            dates.append(parser.parse(row[0]))
            value.append(row[1])
        fig = plt.figure(figsize=(18, 8))
        plt.plot_date(dates, value, '-')
        plt.xlabel('Date and Time')
        plt.ylabel('Values')
        plt.tight_layout()
        img = io.BytesIO() 
        plt.savefig(img, format='png', bbox_inches='tight')
        plt.clf()
        img.seek(0)
        image_data = base64.b64encode(img.getvalue()).decode()
        updattime = cur.execute('SELECT date_time_of_log FROM Log WHERE id=(SELECT max(id) FROM Log WHERE tracker_id={})'.format(tra_id))
        updattime = updattime.fetchone()
        if updattime:
            updattime = ''.join(updattime)
            now = datetime.datetime.now()
            diff = now - parser.parse(updattime)
            ago = str(diff)
            h = ago[:1]
            m = ago[2:4]
            s = ago[5:7]
            return render_template("viewtracker.html", user=curuser,tracker=traker,log=log,hour=h,minute=m,second=s,img=image_data)
        else:
            return render_template("viewtracker.html", user=curuser,tracker=traker,log=log,img=image_data)
    else:
        return redirect(url_for('views.login'))

@views.route('/addlog/<int:tra_id>', methods=['GET','POST'])
def addlog(tra_id):
    if curuser != 0:
        traker = Tracker.query.get(tra_id)
        time = datetime.datetime.now()
        ttype = traker.tracker_type
        multi = str(traker.settings)
        l = list(map(str,multi.split(',')))
        if request.method == 'POST':
            flag = 0
            timestamp = request.form.get('timestamp')
            value =  request.form.get('value')
            note = request.form.get('note')
            if flag == 0:
                newlog = Log(value=value, notes=note, tracker_id=tra_id, user_id=curuser.id,date_time_of_log=str(time),timestamp=timestamp)
                db.session.add(newlog)
                db.session.commit()
                flash("New log added")
                return redirect(url_for('views.viewtracker',tra_id=traker.id))
        return render_template("addlog.html",time=time, user=curuser,tracker=traker,settings=l)
    else:
        return redirect(url_for('views.login'))

@views.route('/deletelog/<int:logid>', methods=['GET','POST'])
def deletelog(logid):
    if curuser != 0:
        logr = Log.query.get(logid)
        db.session.delete(logr)
        db.session.commit()
        flash("Log deleted")
        return redirect(url_for('views.viewtracker',tra_id=logr.tracker_id))
    else:
        return redirect(url_for('views.login'))

@views.route('/editlog/<int:log_id>', methods=['GET','POST'])
def editlog(log_id):
    if curuser != 0:
        logg = Log.query.get(log_id)
        traker_id = logg.tracker_id
        time = datetime.datetime.now()
        traker = Tracker.query.get(traker_id)
        multi = str(traker.settings)
        l = list(map(str,multi.split(',')))
        if request.method == 'POST':
            new_timestamp = request.form.get('timestamp') 
            new_val = request.form.get('value')
            new_note = request.form.get('note')
            logg.timestamp = new_timestamp
            logg.value = new_val
            logg.notes = new_note
            logg.date_time_of_log = time
            db.session.commit()
            flash('Log updated')
            return redirect(url_for('views.viewtracker',tra_id=traker.id))

        return render_template("editlog.html", user=curuser,log=logg,tracker=traker,settings=l)
    else:
        return redirect(url_for('views.login'))