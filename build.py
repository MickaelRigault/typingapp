

# Build the sql file if need and fills the target with the latests IDR
from typingapp import routes
routes.db.create_all()
routes.build_targets_db()
