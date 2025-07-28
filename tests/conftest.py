"""
This module provides reusable fixtures and configurations for the test session
"""
import os
import pytest
import logging as logs
import requests
import subprocess
import time

from contextlib import contextmanager
from faker import Faker
from playwright.sync_api import sync_playwright, Browser, Page
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from typing import Generator, Dict, List

from app.settings import GlobalSettings
from app.database_client import DatabaseClient
from app.models.user import User

# =============================================================================
# Logging Configuration
# =============================================================================

logs.basicConfig(
    level=logs.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logs.getLogger(__name__)

# =============================================================================
# Application Settings Fixture
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def test_settings(request):
    """Provides a session-scoped settings singleton"""
    # set any os.environ variables here
    settings = GlobalSettings()
    yield settings

# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def test_db(request, test_settings):
    """Provides a session-scoped database configuration"""
    logger.info(f"Deploying Test Database at {test_settings.DATABASE_URL}...")
    test_client = DatabaseClient()
    engine = test_client.engine

    logger.info("Dropping existing tables...")
    test_client.model_base.metadata.drop_all(bind=engine)

    logger.info("Creating tables for test session...")
    test_client.model_base.metadata.create_all(bind=engine)
    
    yield test_client

    if request.config.getoption("--preserve-db"):
        logger.info("'--preserve-db' option detected: skipping data teardown")
    else:
        logger.info("Beginning database teardown...")
        test_client.model_base.metadata.drop_all(bind=engine)
        logger.info("Database teardown complete.")

@pytest.fixture
def db_session(request, test_db) -> Generator[Session, None, None]:
    """
    Provides a test-scoped databse session.
    
    Performs a teardown of all tables after each test,
    unless --preserve-db is passed.
    """
    session = next(test_db.get_session())
    try:
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        session.rollback()
        raise
    finally:
        preserve_db = request.config.getoption("--preserve-db")
        if preserve_db:
            logger.info("Skipping table teardown. [--preserve_db]")
        else:
            logger.info("Beginning database teardown...")
            for table in reversed(test_db.model_base.metadata.sorted_tables):
                logger.info(f"Dropping table {table}")
                session.execute(table.delete())
            session.commit()
        session.close()

@contextmanager
def managed_db_session(test_db):
    """
    Context manager for safe database session handling
    Automatically handles rollback and cleanup

    Example:
        with managed_db_session() as session:
            user = session.query(User).first()
    """
    session = test_db.get_session()
    try:
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

# =============================================================================
# Data Record Fixtures & Methods
# =============================================================================

Faker.seed(12345)
data_faker = Faker()

def generate_user_data() -> dict[str, str]:
    """
    Helper funciton for generating user data values

    Returns
    -------
    dict[str, str]
        A dict containing user fields with faked data
    """
    return {
        "first_name": data_faker.first_name(),
        "last_name": data_faker.last_name(),
        "email": data_faker.unique.email(),
        "username": data_faker.unique.user_name(),
        "password": data_faker.password(length=12)
    }

@pytest.fixture
def test_user(db_session: Session) -> User:
    """Creates a single fake User"""
    user_data = generate_user_data()
    user = User(**user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    logger.info(f"Created test user with ID: {user.id}")
    return user

@pytest.fixture
def seed_users(db_session: Session, request) -> List[User]:
    """
    Creates and inserts multiple test users

    Usage:
        @pytest.mark.parametrize("seed_users", [10], indirect=True)
        def test_many_users(seed_users):
            # test logic
    """
    try:
        num_users = request.param
    except AttributeError:
        num_users = 5

    users = []
    for _ in range(num_users):
        user_data = generate_user_data()
        user = User(**user_data)
        users.append(user)
        db_session.add(user)

    db_session.commit()
    logger.info(f"Seeded {len(users)} users into the test database.")
    return users

# =============================================================================
# FastAPI Fixtures & Methods
# =============================================================================

def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for server to be ready, raising an error on timeout"""
    start_time = time.time()
    while(time.time() - start_time) < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    return False

class ServerStartupError(Exception):
    """Raised when the test server fails to start properly"""
    pass

@pytest.fixture(scope="session")
def fastapi_server():
    """Provide a FastAPI test server for integration testing"""
    server_url = 'http://127.0.0.1:8000/'
    logger.info("Starting test server...")

    try:
        process = subprocess.Popen(
            ['python', 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if not wait_for_server(server_url, timeout=30):
            raise ServerStartupError("Failed to start test server")

        logger.info("Test server started successfully.")
        yield server_url

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise
    finally:
        logger.info("Terminating test server...")
        process.terminate()
        try:
            process.wait(timeout=5)
            logger.info("Test server terminated gracefully")
        except subprocess.TimeoutExpired:
            logger.warning("Test server did not terminate in time; killing it")
            process.kill()

# =============================================================================
# Browser and Page Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def browser_context():
    """Provides a Playwright browser context for UI tests."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        logger.info("Playwright browser launched.")
        try:
            yield browser
        finally:
            logger.info("Closing Playwright browser.")
            browser.close()

@pytest.fixture
def page(browser_context: Browser):
    """Provides a new browser page for each test"""
    context = browser_context.new_context(
        viewport={'width': 1920, 'height': 1000},
        ignore_https_errors=True
    )
    page = context.new_page()
    logger.info("Created a new browser page.")
    try: 
        yield page
    finally:
        logger.info("Closing browser page and context.")
        page.close()
        context.close()

# =============================================================================
# Command-Line Options & Test Collection
# =============================================================================

def pytest_addoption(parser):
    """Adds command line options for pytest execution"""
    parser.addoption(
        "--preserve-db",
        action="store_true",
        default=False,
        help="Keep test database records after test execution"
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run tests marked 'slow'"
    )

def pytest_collection_modifyitems(config, items):
    """Automatically skip tests marked 'slow' unless '--run-slow' is passed"""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="test is marked 'slow': use --run-slow to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)











