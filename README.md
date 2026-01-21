[What we have]
- Basic app that communicates with a local PostgreSQL server and handles json requests.

[TODO: What we don't have...]
- Implementing absolutely everything more specific than the aforementioned, i.e. generating tokens, hashed passwords, verifying and sending emails
- Rethinking the database since it heavily depends on the implementation, particularly the (not yet written) module for passwords.
- Refactoring and sticking to one language?...

[Running the project]
You need a PostgreSQL server up and running in order to communicate with a database, otherwise the application is rendered useless.
1. With the SQL server running, edit and execute `database/init.sh` to initialize the database.
2. Install the dependencies in `pyproject.toml` from a virtual environment.
3. Adjust the settings to your PostgreSQL server.
4. Call `fastapi dev` from `app`.
You can access the auto-generated docs through http://127.0.0.1:8000/docs (genuinely useful)

[Project structure]
The purpose of each folder in the project tree is the following:
`database` -> Everything directly related to the SQL, mainly the initialization of the database.
`models` -> SQLModel Python representation of the database tables.
`routes` -> Routes/views/URLs for accessing the api.
`serializers` -> Models to handle the expected body of the requests.
`utils` -> Utility functions related to security and whatnot.


