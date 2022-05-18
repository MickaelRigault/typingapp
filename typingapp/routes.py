import base64
import os
from io import BytesIO

from typingapp import app

import warnings
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
from ztfidr import io
from ztfidr.target import Target

SAMPLE = ztfidr.get_sample()

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
DB_PATH = os.path.join(io.IDR_PATH, "typingapp.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{DB_PATH}'
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ==================== #
#                      #
#   USERS              #
#                      #
# ==================== #
class Users(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    # max 100 caracter cannot be blank
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False,
                      unique=True)  # email is unique
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    # password
    password_hash = db.Column(db.String(120), nullable=False)

    # - Properties
    config__lcplot = db.Column(db.String(100))

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
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """ """
        return check_password_hash(self._password_hash, password)


# ==================== #
#                      #
#   TARGETS            #
#                      #
# ==================== #
class Targets(db.Model):  # created by pandas
    # __searchable__ = ["name"]

    id = db.Column(db.Integer, primary_key=True)

    # max 100 caracter cannot be blank
    name = db.Column(db.String(100), nullable=False, unique=True)
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


NTARGETS = Targets.query.count()

# ==================== #
#                      #
#   TARGET-INFO         #
#                      #
# ==================== #


class Classifications(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    target_name = db.Column(db.String(100), nullable=False)

    # - What kind is stored
    kind = db.Column(db.String(100), nullable=False)
    # - What value is stored
    value = db.Column(db.String(100), nullable=False)

    date_added = db.Column(db.DateTime, default=datetime.utcnow)


# ================ #
#                  #
#    LOGIN         #
#                  #
# ================ #
# Flask Login Stuff
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # where to point to log if needed


@login_manager.user_loader
def load_user(user_id):
    """ """
    try:
        return Users.query.get(int(user_id))
    except:
        return None

# ================ #
#                  #
#    TOOLS         #
#                  #
# ================ #

def get_classified(incl_unclear=False, type_isin=None,
                   from_current_user="current"):
    """ 
    Parameters
    ----------
    
    Returns
    -------
    list of target name
    """
    typed_names = Classifications.query.filter_by(kind="typing")
    if from_current_user:
        typed_names = typed_names.filter_by(user_id=current_user.id)

    if typed_names.count() == 0:
        return []

    if not incl_unclear:
        typed_names = typed_names.filter(
            Classifications.value.isnot("unclear"))

    if type_isin is not None:
        typed_names = typed_names.filter(
            Classifications.value.in_(list(np.atleast_1d(type_isin))))

    return np.concatenate(typed_names.with_entities(Classifications.target_name).distinct().all())


def get_not_classified(incl_unclear=False, type_isin=None, as_basequery=False):
    """ 
    Parameters
    ----------
    
    Returns
    -------
    list of target name
    """
    isclassified = get_classified(
        incl_unclear=incl_unclear, type_isin=type_isin)
    if isclassified is not None and len(isclassified) > 0:
        basequery = Targets.query.filter(Targets.name.notin_(isclassified))
    else:
        basequery = Targets.query

    if as_basequery:
        return basequery
    return np.concatenate(basequery.with_entities(Targets.name).all())

def get_mytargets(user_id):
    """ """
    return pandas.read_sql_query("SELECT * FROM Classifications WHERE value='target:target'"+
                                f" and user_id = {user_id}",
                                 db.engine)
    
# ================ #
#                  #
#    TOOLS DB      #
#                  #
# ================ #

def build_targets_db(iloc_range=None,
                     tablename="targets"):
    """ """
    # Data to Store
    data = io.get_targets_data()
    target_db = data.reset_index().rename({"index": "name",
                                           "sn_ra": "ra", "sn_dec": "dec",
                                           "type": "auto_type", "subtype": "auto_subtype",
                                           "p(type)": "auto_type_prob", "p(subtype|type)": "auto_subtype_prob",
                                           }, axis=1)
    target_db = target_db.reset_index().rename({"index": "id"}, axis=1)

    if iloc_range is None:
        to_store = target_db
    else:
        to_store = target_db.iloc[iloc_range[0]:iloc_range[1]]

    # Actual storing
    to_store.to_sql(tablename, db.engine, if_exists="replace")


def merging_userdb(filepath_db):
    """ """
    import sqlite3
    connew = sqlite3.connect(filepath_db)
    #
    # Merge the user
    #
    # - Current
    current_users = pandas.read_sql_query("SELECT * FROM Users", db.engine)
    # -> new
    newuser = pandas.read_sql_query("SELECT * FROM Users", connew)
    if len(newuser) > 1:
        raise NotImplementedError("Only 1 user DB merge implemented.")
    newuser = newuser.iloc[0]
    newuser_id = newuser["id"] + \
        current_users["id"].max()  # will need it later
    newuser["id"] = newuser_id
    knewuser = newuser.to_dict()
    _ = knewuser.pop("date_added")  # because db sets it automatically.
    # - merging
    user = Users(**knewuser)
    db.session.add(user)
    db.session.commit()
    #
    # Merge the Classifications
    #
    current_classifications = pandas.read_sql_query(
        "SELECT * FROM Classifications", db.engine)
    new_classifications = pandas.read_sql_query(
        "SELECT * FROM Classifications", connew)
    new_classifications["user_id"] = newuser_id
    new_classifications["id"] += current_classifications["id"].max()
    # merging
    for i, newclassification in new_classifications.iterrows():
        c = newclassification.to_dict()
        _ = c.pop("date_added")
        newc = Classifications(**c)
        db.session.add(newc)

    db.session.add(user)
    db.session.commit()

# ================ #
#                  #
#    ROUTES        #
#                  #
# ================ #

@app.route("/")
def home():
    """ """
    current_classifications = pandas.read_sql_query("SELECT * FROM Classifications WHERE kind='typing'",
                                                    db.engine)
    # Remove the unclear
    classifications = current_classifications[~(current_classifications["value"].astype(str) == "unclear")]
    #
    nclassifications = pandas.DataFrame(classifications.groupby("user_id").size().sort_values(ascending=False),
                                        columns=["nclassifications"])
    users = pandas.read_sql_query("SELECT * FROM Users", db.engine).set_index("id")
    nclassifications["name"] = users.loc[nclassifications.index]["name"]
    # Add reports
    current_report = pandas.read_sql_query("SELECT * FROM Classifications WHERE kind='report'",
                                           db.engine)
    nclassifications = pandas.merge(nclassifications,
                                    pandas.DataFrame(current_report.groupby(
                                        "user_id").size(), columns=["nreports"]),
                                    left_index=True, right_index=True)
    # convert to dict for the website.
    dictclass = nclassifications.T.to_dict()

    # n-classifications
    target_classifications = classifications.groupby("target_name").size()
    atleast1_classifications = np.sum(
        target_classifications >= 1)/NTARGETS * 100
    atleast2_classifications = np.sum(
        target_classifications >= 2)/NTARGETS * 100

    # per user classifications

    return render_template("home.html",
                           atleast1_classifications=atleast1_classifications,
                           atleast2_classifications=atleast2_classifications,
                           dictclass=dictclass
                           )


@app.route("/tutorials")
def tutorials():
    """ """
    return render_template("tutorials.html")


# ================ #
#                  #
#    LOGIN/USERS   #
#                  #
# ================ #
# -------- #
#  LOGIN   #
# -------- #
@app.route('/login', methods=["GET", "POST"])
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
                login_user(user)  # Flask login
                flash("Login Successfull", category="success")
                return redirect(url_for("dashboard"))
            else:
                flash("Wrong Password - Try again", category="error")
        else:  # no user
            flash("That user doesn't exist - Try again", category="warning")

    return render_template("login.html", form=form)


@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out", category="warning")
    return redirect(url_for('login'))

# DashBoard dashboard


@app.route('/dashboard', methods=["GET", "POST"])
@login_required
def dashboard():
    """ """
    return render_template("dashboard.html")

# -------- #
#  USER    #
# -------- #
@app.route("/user/list")
@login_required
def user_list():
    """ """
    our_users = Users.query.order_by(Users.date_added)
    return render_template("user_list.html", our_users=our_users)


@app.route("/user/add", methods=["GET", "POST"])
def add_user():
    """ """
    form = UserForm()
    if form.validate_on_submit():  # If you submit, this happens

        # query the Users-Database that have the inout user email and return the first one
        # This should return None if it is indeed unique
        user = Users.query.filter_by(username=form.username.data).first()
        if user is None:
            # create a new db user entry
            hashed_pwd = generate_password_hash(
                form.password_hash.data, "sha256")

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
            flash("Username already used. User not added to the database",
                  category="error")

        # Clearing this out
        name = form.name.data
        form.username.data = ''
        form.name.data = ''
        form.email.data = ''
        form.password_hash.data = ''

    return render_template("add_user.html", form=form)


@app.route("/update/user", methods=["GET", "POST"])
@login_required
def update_user():
    """ """
    name_to_update = Users.query.get_or_404(current_user.id)
    #
    if request.method == "POST":  # Similar to the other one. Did they do something
        input_keys = list(request.form.keys())
        if len(input_keys) > 0 and input_keys[0] == "config__lcplot":
            name_to_update.config__lcplot = request.form["config__lcplot"].strip(
            )
        else:
            flash("Unknown configuration to change", category="warning")

        try:
            db.session.commit()
            flash("Config changed successful", category="success")
        except:
            flash("Error: looks like threre was a problem... try again",
                  category="error")

    return redirect(url_for("dashboard"))


@app.route("/update/password", methods=["GET", "POST"])
@login_required
def update_password():
    """ """
    form = UserForm()
    #
    if request.method == "POST":  # Did they do something
        if request.form["newpassword_hash"] != request.form["password_hash_matched"]:
           flash("New Password do not match - Try again", category="error")
           return redirect(url_for("update_password"))

        user = Users.query.get_or_404(current_user.id)
        old_password = request.form["password_hash"]
        if not check_password_hash(user.password_hash, old_password):
            flash("Wrong Password - Try again", category="error")
            return redirect(url_for("update_password"))

        hashed_pwd = generate_password_hash(
            request.form["newpassword_hash"], "sha256")
        user.password_hash = hashed_pwd
        try:
            db.session.commit()
            flash("Password Updated Successfully", category="success")
        except:
            flash("Error: looks like threre was a problem... try again",
                  category="error")

        return redirect(url_for("dashboard"))

    return render_template("update_password.html", form=form)


@app.route("/delete/<int:id>")
@login_required
def delete_user(id):
    """ """
    user_to_delete = Users.query.get_or_404(
        id)  # get the DB entry associated to the id
    name = None  # because first time we load, it will be None.
    try:
        # change made to the session, then you need to commit
        db.session.delete(user_to_delete)
        db.session.commit()
        flash("User Deleted Successfully", category="success")
    except:
        flash("Whoops! There was a probleme deleting the user.", category="error")

    our_users = Users.query.order_by(Users.date_added)
    return redirect(url_for("add_user"))



# ================ #
#                  #
#  CLASSIFICATION  #
#                  #
# ================ #

@app.route("/rmclassification/<int:id>")
@login_required
def delete_classification(id):
    """ """
    classification_to_delete = Classifications.query.get_or_404(
        id)  # get the DB entry associated to the id

    name = None  # because first time we load, it will be None.
    try:
        # change made to the session, then you need to commit
        db.session.delete(classification_to_delete)
        db.session.commit()
        flash("Classification deleted successfully", category="success")
    except:
        flash("Whoops! There was a probleme deleting the classification.",
              category="error")

    return redirect(url_for("classifications"))


@app.route("/clearclassifications")
@login_required
def clear_classifications():
    """ """
    db.session.query(Classifications).filter_by(
        user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for("classifications"))


@app.route("/classify/<int:id>", methods=["GET", "POST"])
@login_required
def classify(id, flash_classified=False):
    """ """
    # - Target action made to
    target = Targets.query.get_or_404(id)  # get the DB entry
    # associated to the id

    # Information are contained withing this
    input_keys = list(request.form.keys())[0]

    # ---------------- #
    # Action Made      #
    # ---------------- #
    if request.method == "POST":

        # Classification
        if input_keys == "typing":  # This is a classification
            value = request.form["typing"]
            classification = Classifications(user_id=current_user.id,
                                             target_id=id,
                                             target_name=target.name,
                                             kind="typing",
                                             value=value.strip().lower()
                                             )
            if flash_classified:
                if value.lower() == "unclear":
                    flash(
                        f"Unclear classification for {target.name}", category="warning")
                else:
                    flash(
                        f"You classified {target.name} as {value}", category="success")

            db.session.add(classification)
            db.session.commit()
            return redirect(url_for("target_random"))

        elif "report:" in input_keys:  # report
            kind = "report"
            value = input_keys.replace("report:", "")

            classification = Classifications(user_id=current_user.id,
                                             target_id=id,
                                             target_name=target.name,
                                             kind=kind,
                                             value=value.strip().lower()
                                             )

            flash(f"You reported {value} for {target.name}",
                  category="warning")
            db.session.add(classification)
            db.session.commit()
            return redirect(url_for(f"target_page", name=target.name,
                                    warn_report=False))

        elif "skip" in request.form:
            flash(f"You skipped {target.name} | no db update",
                  category="secondary")
            return redirect(url_for("target_random"))

    flash(
        f"Classication/Report action Failed input_keys: {input_keys}", category="danger")
    return redirect(url_for(f"target_page", name=target.name, warn_report=False))


@app.route("/classifications")
@login_required
def classifications():
    """ """
    classifications = Classifications.query.order_by(
        Classifications.id).filter_by(user_id=current_user.id)
    return render_template("classifications.html", classifications=classifications)


@app.route("/classifications/all")
@login_required
def all_classifications():
    """ """
    classifications = Classifications.query.order_by(Classifications.id)
    return render_template("classifications.html", classifications=classifications)

# ================ #
#                  #
#  TARGET          #
#                  #
# ================ #

@app.route("/search", methods=["GET", "POST"])
def search():
    """ """
    if request.method == "POST":
        target_name = request.form["name"]
        return redirect(url_for(f"target_page", name=target_name))
    else:
        return redirect(url_for("home"))


@app.route("/target/list")
@login_required
def target_list():
    """ """
    targets = Targets.query.order_by(Targets.id)
    return render_template("target_list.html", targets=targets)


@app.route("/target/list/favorite")
@login_required
def my_target_list():
    """ """
    list_of_names = get_mytargets(current_user.id).target_name.astype("string").values
    targets = Targets.query.filter( Targets.name.in_(list_of_names)
                                  ).order_by(Targets.id)

    return render_template("target_list.html", targets=targets)


@app.route("/targetid/<id>")
@login_required
def targetid_page(id):
    """ """
    target = Targets.query.get_or_404(id)
    return target_page(target.name)


@app.route("/target/<name>")
@login_required
def target_page(name, warn_typing=True, warn_report=True):
    """ """
    ZQUALITY_LABEL = {2: " z source: host",
                      1: " z source: sn",
                      0: " z source: unknown",
                      None: " z source: not given"}

    from matplotlib.figure import Figure
    
    # DB
    targetname = escape(name)
    target = Targets.query.filter_by(name=targetname).first()

    # = Requesting page = #
    # input arguments 
    args = request.args

    # Parsing inputs
    # annoying the False/True are strings...
    if eval(args.get("warn_typing", default=str(warn_typing), type=str)):
        t_typings = Classifications.query.filter_by(kind="typing",
                                                    target_name=targetname, user_id=current_user.id).all()
        for t_typing in t_typings:
            flash(
                f"You already classify this target ({target.name}) as {t_typing.value}", category="warning")

    if eval(args.get("warn_report", default=str(warn_report), type=str)):
        t_reports = Classifications.query.filter_by(kind="report",
                                                    target_name=targetname, user_id=current_user.id).all()
        for t_report in t_reports:
            flash(
                f"You already reported {t_report.value} this target ({target.name})", category="info")

    # ---------- #
    #    Data    #
    # ---------- #
    
    lightcurve = SAMPLE.get_target_lightcurve(name)
    spectra = np.atleast_1d(SAMPLE.get_target_spectra(name))
    
    redshift, zlabel = SAMPLE.data.loc[name][["redshift","redshift_source"]].values
    t0, t0_err = SAMPLE.data.loc[name][["t0","t0_err"]].values
    # ------------ #
    # - LC Plot    #
    # ------------ #
    buflc = BytesIO()
    axlc = Figure(figsize=[7, 2]).add_axes([0.08, 0.25, 0.87, 0.7])

    # - Spectra Plots
    spectraplots = []
    for spec_ in np.atleast_1d(spectra):
        if spec_ is None or spec_.snidresult is None:
            continue
        
        # Figure
        buf = BytesIO()
        fig = Figure(figsize=[9, 3])
        
        # Phase
        phase, dphase = spec_.get_phase(t0, redshift), t0_err
        datetime = spec_.get_obsdate().datetime
        
        # -> Adding phase on the LC plot
        axlc.axvline(datetime, ls="--", color="0.6", lw=1)
        # -> Plot the spectrum
        _ = spec_.snidresult.show(fig=fig, label=spec_.filename.split("/")[-1],
                                  phase=phase, dphase=dphase, redshift=redshift, zlabel=zlabel
                                  ).savefig(buf, format="png", dpi=250)
        spectraplots.append(base64.b64encode(buf.getbuffer()).decode("ascii"))

    # - Storing the LC plot    #
    try:
        if current_user.config__lcplot == "None" or current_user.config__lcplot == None or current_user.config__lcplot == "flux":
            figlc = lightcurve.show(ax=axlc)
        else:
            figlc = lightcurve.show(ax=axlc, inmag=True)

        _ = figlc.savefig(buflc, format="png", dpi=250)
        lcplot = base64.b64encode(buflc.getbuffer()).decode("ascii")
    except:
        warnings.warn(f"Cannot build the LC for {name}")
        lcplot = None

    # Delete the 
    del lightcurve
    del spectra

    #
    if target:
        return render_template("target.html",
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
    targetname = get_not_classified(
        as_basequery=True).order_by(func.random()).first().name
    return target_page(targetname)
