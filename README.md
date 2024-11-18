# E-Affidavit BACKEND
## Content
- [How to run the project](#how-to-run-the-project)
- [Project Dependencies](#project-dependencies)
- [Deployment environments](#deployment-environments)
- [How to contribute to the project](#contribution-guidelines)

## How To Run The Project
In order to run the project, you need to clone the repository

```
git clone  https://github.com/myhousingpal/back_end.git
```


## Install Dependencies
run poetry shell

then poetry install -- to install dependencies


### With uvicorn:

```
uvicorn app.main:app
```

Specifying host and port:
```
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

During development where you don't want to keep restarting the application you can add a reload option as shown below:
```
uvicorn app.main:app --reload
```
or
```
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload


## Project Dependencies
### Database(s)

1. Mongo Db
: This is used to store unrelational data in collection
: Example - Templates, Documents

2. Postgres

: This is used to store data that have relationships and connections
: Example - Users, Courts etc

### commonLib
This folder specifies models and schema definitions to be used accross the project and is stored in it's own repository -

## Deployment Environments
1. **dev**: This environment is meant for the backend developers to test new implementations on a production like environment.

    Link -  https://e-affidavit-backend.onrender.com

2. **staging**: This environment is meant to be used by the QA for testing purposes. Any issues discovered here are communicated with the developers and the necessary changes are made. Once the features on the staging environment are accepted, they can then be pushed to the prod environment.

    Link - https://back-end-y8ed.onrender.com

3. **prod**: This environment is meant for the end users. It consists of the most recent and most stable features. This environment is only pushed to when all features have been tested and confirmed accross the dev and staging environment. It is also the environment that is used by the frontend prod environment
        Link - https://e-affidavit-api.azurewebsites.net/


**Note**: This method of deployment is subject to change as the project develops, and should not be taken as a concrete standard.



## Contribution Guidelines


**Steps:**

1. Clone the repositoy

2. Create a branch with your name

3. Add the necessary features, changes and then commit.

    Your commit message title should indicate the nature of the task, which could be either feat/fix/chore.

    Example 1: feat: add organization delete

    Example 2: fix: modify syntax error
    
    Example 3: chore: move models folder

4. Push your changes to your branch

5. Make a pull request to the dev branch, request a reviewer and wait for feedback, comment or acceptance before merging.
