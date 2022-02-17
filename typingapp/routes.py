import base64
import os
from io import BytesIO

from typingapp import app

import numpy as np
import pandas
from .forms import UserForm, LoginForm


from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, login_required, logout_user, current_user
from markupsafe import escape

# =========== #
#             #
#   ZTFIDR    #
#             #
# =========== #
import ztfidr
from ztfidr.target import Target


# ================ #
#                  #
#    DATABASE      #
#                  #
# ================ #

from datetime import datetime

# DataBase Imports
from sqlalchemy.sql import func
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# user logins
from flask_login import UserMixin, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash


# -------------- #
# LOCAL DATABASE #
# -------------- #
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///users.db'
db = SQLAlchemy(app)
DB_PATH  = os.path.join( os.path.dirname(__file__), "users.db")


# ==================== #
#                      #
#   USERS              #
#                      #
# ==================== #
class Users( db.Model, UserMixin ):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False) # max 100 caracter cannot be blank 
    email = db.Column(db.String(100), nullable=False, unique=True) # email is unique
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    # password
    password_hash = db.Column(db.String(120), nullable=False)
    
    # User can make Many Classification

    # Create A String
    def __repr__(self):
        return f"<Name {self.name}>"

    # ----------- #
    #  Property   #
    # ----------- #
    @property
    def password(self):
        """ """
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        """ """
        self.password_hash = generate_password_hash( password )

    def verify_password(self, password):
        """ """
        return check_password_hash(self._password_hash, password)

    
# ==================== #
#                      #
#   TARGETS            #
#                      #
# ==================== #
class Targets( db.Model ): # created by pandas
    # __searchable__ = ["name"]
    
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(100), nullable=False, unique=True) # max 100 caracter cannot be blank
    # Coordinates
    ra = db.Column(db.Float())
    dec = db.Column(db.Float())
    # Redshift
    redshift = db.Column(db.Float())
    z_quality = db.Column(db.Integer())
    # Typing    
    auto_type = db.Column(db.String(100))
    auto_subtype = db.Column(db.String(100))
    auto_type_prob = db.Column(db.Float())
    auto_subtype_prob = db.Column(db.Float())

    # Host
    host_ra = db.Column(db.Float())
    host_dec = db.Column(db.Float())

    #
    #
    
# ==================== #
#                      #
#   TARGET-INFO         #
#                      #
# ==================== #

class Classifications( db.Model ):

    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column( db.String(100), nullable=False)
    target_id = db.Column( db.String(100), nullable=False)
    sntype = db.Column( db.String(100), nullable=False)

    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    
    
#subs = db.Table("classification",
#                    db.Column("classifier_id", db.Integer, db.ForeignKey('users.id') ),
#                    db.Column("target_id", db.Integer, db.ForeignKey('targets.id') ),
#s                    )

    
    
    
        
# ================ #
#                  #
#    LOGIN         #
#                  #
# ================ #
# Flask Login Stuff
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # where to point to log if needed

@login_manager.user_loader
def load_user(user_id):
    """ """
    try:
        return Users.query.get( int(user_id) )
    except:
        return None


# ================ #
#                  #
#    TOOLS         #
#                  #
# ================ #
NON_CLASSIFICATIONS = ["Unclear","Report", "Skipper"]
CLASSIFICATIONS = ["SN Ia","NotIa"]
SUBCLASSIFICATIONS = []
    
def get_classifications_df():
    """ """
    df = pandas.read_sql("classifications", con=db.engine)
    df["sntype"] = df.sntype.str.strip().replace("SNe","SN").replace("SN II","NotIa")
    return df

def build_targets_db(db_path, iloc_range=None, tablename="Targets"):
    from ztfidr import io
    import sqlite3
    
    data = io.get_targets_data()
    target_db = data.reset_index().rename({"index":"name",
                               "sn_ra":"ra","sn_dec":"dec",
                                "type":"auto_type", "subtype":"auto_subtype",
                                "p(type)":"auto_type_prob","p(subtype|type)":"auto_subtype_prob",
                              }, axis=1)
    target_db = target_db.reset_index().rename({"index":"id"}, axis=1)


    
    con = sqlite3.connect(db_path)
    if iloc_range is None:
        to_store = target_db
    else:
        to_store = target_db.iloc[iloc_range[0]:iloc_range[1]]
        
    to_store.to_sql(tablename, con, if_exists="replace")
    


# ================ #
#                  #
#    ROUTES        #
#                  #
# ================ #
@app.route("/")
def home():
    """ """
#    ntargets = Targets.query.count()
#    classificationdf = get_classifications_df()
#    nclassified = len(classificationdf[~classificationdf["sntype"].isin(["Unclear","Report", "Skipper"])])
    
#    fclassified = nclassified/ntargets
#    typeserie = classificationdf["sntype"].value_counts().sort_values()
    return render_template("home.html", fraction=50)


# ================ #
#                  #
#    LOGIN/USERS   #
#                  #
# ================ #
# -------- #
#  LOGIN   #
# -------- #
@app.route('/login', methods=["GET","POST"])
def login():
    """ """
    form = LoginForm()
    # entry the if went hit submit from login.html 
    if form.validate_on_submit():
        # grab the first user given the inputform username
        user = Users.query.filter_by(username=form.username.data).first()
        if user:
            # Check the hash
            if check_password_hash(user.password_hash, form.password.data):
                login_user(user) # Flask login
                flash("Login Successfull", category="success")
                return redirect( url_for("dashboard") )
            else:
                flash("Wrong Password - Try again", category="error")
        else: # no user
            flash("That user doesn't exist - Try again", category="warning")
                
    return render_template("login.html", form=form)

@app.route("/logout", methods=["GET","POST"])
@login_required 
def logout():
    logout_user()
    flash("You have been logged out", category="warning")
    return redirect( url_for('login') )

# DashBoard dashboard
@app.route('/dashboard', methods=["GET","POST"])
@login_required 
def dashboard():
    """ """
    return render_template("dashboard.html")

# -------- #
#  USER    #
# -------- #
@app.route("/user/list")
def user_list():
    """ """        
    our_users = Users.query.order_by(Users.date_added)
    return render_template("user_list.html", our_users=our_users)

@app.route("/user/add", methods=["GET","POST"])
def add_user():
    """ """
    name = None
    form = UserForm()
    if form.validate_on_submit(): # If you submit, this happens
        # query the Users-Database that have the inout user email and return the first one
        # This should return None if it is indeed unique
        user = Users.query.filter_by(username=form.username.data).first()
        if user is None:
            # create a new db user entry
            hashed_pwd = generate_password_hash(form.password_hash.data, "sha256")
            
            user = Users(username=form.username.data,
                         name=form.name.data,
                         email=form.email.data,
                         password_hash=hashed_pwd)
            
            # add it to the actual db
            db.session.add(user)
            # and commit it
            db.session.commit()
            flash("User added successfully", category="success")
        else:
            flash("Username already used. User not added to the database", category="error")
            
        # Clearing this out
        name = form.name.data
        form.username.data = ''
        form.name.data = ''
        form.email.data = ''
        form.password_hash.data = ''
        
    our_users = Users.query.order_by(Users.date_added)
    return render_template("add_user.html", form=form, name=name, our_users=our_users)

@app.route("/update/<int:id>", methods=["GET","POST"])
def update_user(id):
    """ """
    form = UserForm()
    name_to_update = Users.query.get_or_404(id)
    # 
    if request.method == "POST": # Similar to the other one. Did they do something
        name_to_update.username  = request.form["username"]
        name_to_update.name  = request.form["name"]
        name_to_update.email  = request.form["email"]
        try:
            db.session.commit()
            flash("User Updated Successfully", category="success")
        except:
            flash("Error: looks like threre was a problem... try again", category="error")
            
        return redirect( url_for("dashboard") )
                                 
    else: # Or just went to the page
        return render_template("update_user.html", form=form,
                                       name_to_update=name_to_update)

@app.route("/delete/<int:id>")
def delete_user(id):
    """ """
    user_to_delete = Users.query.get_or_404(id) # get the DB entry associated to the id
    name = None # because first time we load, it will be None.
    try:
        db.session.delete(user_to_delete) # change made to the session, then you need to commit
        db.session.commit()        
        flash("User Deleted Successfully", category="success")
    except:
        flash("Whoops! There was a probleme deleting the user.", category="error")

    our_users = Users.query.order_by(Users.date_added)
    return redirect( url_for("add_user") )
        

# ================ #
#                  #
#  TARGET          #
#                  #
# ================ #
@app.route("/search", methods=["GET","POST"])
def search():
    """ """
    if request.method == "POST":
        target_name = request.form["name"]
        flash(f"You search for {target_name}", category="warning")
        return redirect( url_for(f"target_page", name=target_name) )
    else:
        return redirect( url_for("home") )

@app.route("/target/list")
def target_list():
    """ """        
    targets = Targets.query.order_by(Targets.id)
    return render_template("target_list.html", targets=targets)

@app.route("/target/<name>")
@login_required
def target_page(name):
    """ """
    ZQUALITY_LABEL = {2:" z source: host",
                      1:" z source: sn",
                      0:" z source: unknown",
                      None:" z source: not given"}


    
    from matplotlib.figure import Figure
    
    targetname = escape(name)
    target = Targets.query.filter_by(name=targetname).first()
    t_ = Target.from_name(name)
    redshift, z_quality = t_.get_redshift()        


    # ------------ #
    # - LC Plot    #
    # ------------ #
    buflc = BytesIO()
    axlc = Figure(figsize=[7,2]).add_axes([0.08,0.25,0.87,0.7])
    
    # - Spectra Plots
    spectraplots = []
    for spec_ in np.atleast_1d(t_.spectra):
        if spec_ is None or spec_.snidresult is None:
            continue
        # Figure
        buf = BytesIO()
        fig = Figure(figsize=[9,3])
        # Data        
        phase, dphase = spec_.get_phase(t_.salt2param["t0"]), t_.salt2param["t0_err"]
        # - Adding phase on the LC plot
        axlc.axvline(spec_.get_obsdate().datetime, ls="--", color="0.6", lw=1)
        
        zlabel = ZQUALITY_LABEL[z_quality]
        _ = spec_.snidresult.show(fig=fig, label=spec_.filename.split("/")[-1],
                                  phase=phase, dphase=dphase, redshift=redshift, zlabel=zlabel
                                  ).savefig(buf, format="png", dpi=250)
        spectraplots.append(base64.b64encode(buf.getbuffer()).decode("ascii"))

    # - Storing the LC plot    #
    figlc = t_.lightcurve.show(ax=axlc)
    _ = figlc.savefig(buflc, format="png", dpi=250)
    lcplot = base64.b64encode(buflc.getbuffer()).decode("ascii")

    del t_
    
    #
    if target:
        return render_template("targetflexible.html",
                                   target=target,
                                   spectraplots=spectraplots,
                                   lcplot=lcplot)
    else:
        flash(f"No Target named {target}", category="warning")
        return render_template("notarget.html", name=targetname)
    
    
@app.route("/target/random")
@login_required
def target_random():
    """ """
    targetname = Targets.query.order_by(func.random()).first().name
    return target_page(targetname)

    
@app.route("/classify/<int:id>", methods=["GET","POST"])
@login_required
def classify(id):
    """ """
    target = Targets.query.filter_by(id=id).first()
    if request.method == "POST":
        # Classification
        if "typing" in request.form:
            typing = request.form["typing"]    
            classification = Classifications(user_id=current_user.id,
                                             target_id=id,
                                             sntype=typing)
            if typing == "Unclear":
                flash(f"Unclear classification for {target.name}", category="warning")
            else:
                flash(f"You classified {target.name} as {typing}", category="success")
            db.session.add(classification)
            db.session.commit()

            return redirect( url_for("target_random") )
        
        # Report                
        if "report" in request.form:
            report = request.form["report"]    
            classification = Classifications(user_id=current_user.id,
                                             target_id=id,
                                             sntype=report)
            if "Emission line" in report:
                flash(f"You reported an emission line for {target.name}", category="info")
            else:
                flash(f"You reported a {report} issue for {target.name}", category="error")
            db.session.add(classification)
            db.session.commit()

            return redirect( url_for(f"target_page", name=target.name) )

        if "skip" in request.form:
            flash(f"You skipped {target.name} | no db update", category="secondary")
            return redirect( url_for("target_random") )
                
    flash(f"Typing Failed updated")
    return redirect( url_for("target_random") )

@app.route("/classifications")
@login_required
def classifications():
    """ """
    classifications = Classifications.query.order_by(Classifications.id)
    return render_template("classifications.html", classifications=classifications)
    
    
