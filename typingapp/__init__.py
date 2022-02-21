__version__="0.2.0"

from flask import Flask

app = Flask(__name__)

app.config['SECRET_KEY'] = "this_is_the_secretkey"
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
#app.run(debug=True, host='0.0.0.0')

import typingapp.routes
