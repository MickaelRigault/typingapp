

# Build the sql file if need and fills the target with the latests IDR

from typingapp import app, io, routes

app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{io.DB_PATH}'
_ = routes.db.create_all()
_ = io.build_targets_db()

