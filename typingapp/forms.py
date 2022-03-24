# WhatTheForm
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError
from wtforms.validators import DataRequired, EqualTo, Length

# Create a Form Class
class UserForm( FlaskForm ):
    username = StringField("Username", validators=[DataRequired()] )
    name = StringField("Name", validators=[DataRequired()] )    
    email = StringField("Email", validators=[DataRequired()] )
    favorite_color = StringField("Favorite Color")
    password_hash = PasswordField("Password", validators=[DataRequired(),
                                                    EqualTo('password_hash_matched',
                                                            "password must match")] )
    newpassword_hash = PasswordField("New password", validators=[DataRequired(),
                                                    EqualTo('password_hash_matched',
                                                            "password must match")] )

    password_hash_matched = PasswordField("Confirm Password",
                                              validators=[DataRequired()]
                                              )
    
    submit = SubmitField("Submit") # For the button


    config__lcplot = StringField("config__lcplot")
    

# Create LoginForm
class LoginForm( FlaskForm ):
    username = StringField("Username", validators=[DataRequired()] )
    password = PasswordField("Password", validators=[DataRequired()] )
    submit = SubmitField("Submit") # For the button    

    
class ClassForm( FlaskForm ):

    username = StringField("Username" )
    targetname = PasswordField("targetname")
    snia = SubmitField("Submit") # For the button    
