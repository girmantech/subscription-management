# Subscription Management

## Backend Setup

### Prerequisites

- Python 3.x (created with Python 3.11)
- Docker
- Docker Compose
- PostgreSQL (if not using Docker)

### Steps
1.  Navigate to `subscription-management` directory:
    ```sh
    cd subscription-management
    ```

2.  Create a virtual environment (optional but recommended):
    ```
    python3 -m venv venv
    source venv/bin/activate  # For Linux/macOS
    venv\Scripts\activate     # For Windows
    ```

3.  Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4.  Set up environment variables (create a .env file in the same directory based on .env.example):
    ```
    cp .env.example .env
    ```
    Update the .env file with your configuration values (if required).

5.  **Database Setup**  
    If using Docker, you can use docker-compose to setup the database. Otherwise, ensure PostgreSQL is installed and accessible.
    ```sh
    docker compose up -d
    ```

6.  Apply database migrations:
    ```
    python3 manage.py migrate
    ```

7.  Run the server:
    ```
    python3 manage.py runserver
    ```
    The server runs at localhost:8000.
