__version__="0.4.0"

from flask import Flask

app = Flask(__name__)

app.config['SECRET_KEY'] = "this_is_the_secretkey"
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

import typingapp.routes

if __name__ == "__main__":
    app.run(host="127.0.0.1", port="8000")
