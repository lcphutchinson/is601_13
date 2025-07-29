# Module 12: RESTful API Routes and Registration/Login finalization.
![Coverage Badge](https://github.com/lcphutchinson/is601_13/actions/workflows/ci-cd.yml/badge.svg)

A module of is601 Web Systems Development, by Keith Williams

This module connects previously implemented validation and ORM logics with BREAD endpoints for users and calculations

See the Dockerhub Repo [[Here]](https://hub.docker.com/repository/docker/lcphutchinson/is601_13)

## Reflection Component

This has been a tough but rewarding week. Untangling Module 12 was quite a task, and difficulties from that effort bled into this module as I integrated the front end code (which I only minimally edited. I've worked very little with HTML and was much more focused on backend problems.) Integrating the front end components and seeing the scope and detail of error messaging smashed into "500 Internal Server Error" really put into perspective the importance of vigorous testing. Many bugs were more difficult to address than usual in this stage of development, but I want to focus on two that involve the 422 Unprocessable Entity Error.

I got this error twice while implementing module 13. First, I would receive this error whenever I interacted with any of the Calculation Routes. I had not fully implemented the test suite for these routes or I may have discovered the nature of the error sooner, but I was able to temporarily adjust the dashboard page to display the error message `{"detail":[{"type":"missing","loc":["query","db"],"msg":"Field required","input":null}]}`. This was easy to identify, but "db" referred to a parameter I had properly typed and encapsulated with Depends(), and so I struggled for hours to figure out why this error was throwing for the Calculation Routes but not for the Registration or Login routes. AI insisted my singleton DatabaseClient was to blame, but eventually I found the answer: get_current_active_user, also called on all the Calculation routes, depended on get_current_user, which used another variable called db that was not properly type hinted. What a mess to have spent hours haggling with ChatGPT and StackOverflow over.

The second time was less frustrating, and something I noticed when attempting to manually recreate certain test scenarios like bad passwords. At first, I thought incorrect passwords were causing 422 errors, but I later found that the structure of our Schema objects was creating cases where the bounds of the schema were violated by inputs coming in from the front-end and were throwing errors that couldn't be checked on the backend as they were wrapped up in the routing pipeline (for example, if a login form had too short a password in it, that data would be passed to main.py where the our decorated login route would attempt to put the data in a LoginForm schema object, triggering a Validation Error that couldn't be caught in the route function code, which then triggered a 422) After discovering this, I have updated many of the "forms" schema that structure incoming code from the frontend to be more accepting, relying on the front-end validation to provide appropriate boundaries for inputs. As of this writing, I believe I still need to put maximum length boundaries on some of those inputs on the front end, but will add those before the final.

### Running the Test Suite

After cloning the repo to your local machine, create and enter virtual environment with the venv module

```bash
python3 -m venv venv
source venv/bin/activate
```

Then, from the root folder, install the project's requirements

```bash
pip install -r requirements.txt
playwright install
```

You may be prompted by playwright to install some dependencies it needs, but its instructions are clear.
Next, deploy the docker image in daemon mode to reserve your terminal for testing.

```bash
docker compose up --build -d
```

After configuration is finished, run the test suite

```bash
pytest
```

### Running the Calculator

After booting up the image, you can access the web page directly with `http://localhost:8000` and the API specification with `http://localhost:8000/docs`
The primary page contains links for registration and login, which will redirect you to the calculations dashboard
