# Subscription Management

## Backend Setup (Local)

### Prerequisites
- Git
- Python 3.x (created with Python 3.11.10)
- Docker
- Docker Compose
- PostgreSQL (if not using Docker)

### Steps
1. Clone the repository on your local machine:
    ```sh
    git clone https://github.com/girmantech/subscription-management.git
    ```

2.  Navigate to `subscription-management` directory:
    ```sh
    cd subscription-management
    ```

3.  Create a virtual environment (optional but recommended):
    ```sh
    python3 -m venv venv
    source venv/bin/activate  # for Linux/macOS
    venv\Scripts\activate     # for Windows
    ```

4.  Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

5.  Set up environment variables (create a .env file in the same directory based on .env.example):
    ```
    cp .env.example .env
    ```
    Update the .env file with your configuration values (as per requirements).

6.  **Set up the database**:  
    If using Docker, you can use docker-compose to setup the database. Otherwise, ensure PostgreSQL is installed and accessible.
    ```sh
    docker compose up -d
    ```

7.  Apply database migrations:
    ```sh
    python3 manage.py migrate
    ```

8.  Add cron jobs:
    ```
    python3 manage.py crontab add
    ```

    In case, you need to remove the cron jobs:
    ```
    python3 manage.py crontab remove
    ```


9.  Run the server:
    ```sh
    python3 manage.py runserver
    ```
    The server runs at localhost:8000.


## Backend Setup (EC2)
***Note**: The instructions below are for **Amazon Linux** operating system instance.*

### Instructions for setting up the project
1. Connect to the instance using terminal on your local machine via SSH using the location of the private key (`.pem` file), the username (`ec2-user` in this case) and the public DNS or IP address:
    ```sh
    sudo ssh -i /path/key-pair-name.pem ec2-user@instance-public-dns-address
    ```

2. Install git on the instance:
    ```sh
    sudo yum update -y
    ```
    ```sh
    sudo yum install git -y
    ```
    ```sh
    git --version
    ```

4. Install Python3.x on the instance *(check the Python versions [here](https://www.python.org/downloads/) in case of any change)*:
    ```sh
    sudo yum install gcc openssl-devel bzip2-devel libffi-devel zlib-devel -y
    ```
    ```sh
    wget https://www.python.org/ftp/python/3.11.10/Python-3.11.10.tgz
    ```
    ```sh
    tar xzf Python-3.11.10.tgz
    ```
    ```sh
    cd Python-3.11.10
    ```
    ```sh
    sudo ./configure --enable-optimizations
    ```
    ```sh
    sudo make altinstall
    ```
    ```sh
    sudo rm -f ../Python-3.11.10.tgz
    ```

5. Create a directory for base solution projects *(optional as per requirements)*:
    ```sh
    # if need to move to root directory
    cd ~
    ```
    ```sh
    mkdir base_solution
    ```
    ```sh
    cd base_solution
    ```

6. Clone the subscription-management repository:
    ```sh
    git clone https://github.com/girmantech/subscription-management.git
    ```

7.  Navigate to `subscription-management` directory:
    ```sh
    cd subscription-management
    ```

8.  Create a virtual environment:
    ```sh
    python3.11 -m venv venv
    source venv/bin/activate
    ```

9.  Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

10. Set up environment variables (create a .env file in the same directory based on .env.example):
    ```sh
    cp .env.example .env
    ```
    Update the .env file with your configuration values (as per requirements):
    ```sh
    nano .env
    ```

11. Make changes to Django settings in order to connect to RDS and allow requests from other hosts:
    ```sh
    nano subscription-management/backend/settings.py
    ```

    Edit the file to make the following changes:
    ```python
    ALLOWED_HOSTS = ['*']

    USE_AWS_RDS = True
    ```

12. Apply database migrations:
    ```sh
    python3.11 manage.py migrate
    ```

13. Add cron jobs:
    ```
    python3.11 manage.py crontab add
    ```

    In case, you need to remove the cron jobs:
    ```
    python3.11 manage.py crontab remove
    ```

14. Test by running the server:
    ```sh
    python3.11 manage.py runserver
    ```
    Use Ctrl + C to stop the server.

15. Install Gunicorn:
    ```sh
    pip install gunicorn
    ```
    Test your application with Gunicorn:
    ```sh
    gunicorn --bind 0.0.0.0:8000 backend.wsgi:application
    ```
    Use Ctrl + C to stop the server.

### Instructions for configuring EC2 instance settings to access the application from local machine
Make sure your EC2 instance's security group is configured to allow inbound traffic on port 80 (HTTP).  
To check and configure this:
1.  Go to the EC2 Dashboard in the AWS Management Console.

2.  Select your instance and scroll down to the Security groups section.

3.  Click on the security group linked to your instance.

4.  In the Inbound rules tab, ensure there is a rule that allows traffic on port 80:  
    **Type**: HTTP  
    **Protocol**: TCP  
    **Port Range**: 80  
    **Source**: 0.0.0.0/0 *(this allows access from anywhere, adjust it for security if necessary)*

### Instructions for configuring Nginx and Gunicorn (for deployment)
1.  Install and start Nginx on the instance:
    ```sh
    sudo yum install nginx -y
    ```
    ```sh
    sudo systemctl start nginx
    ```
    ```sh
    sudo systemctl status nginx
    ```
    The service should be active.  
    **To ensure that everything is set up correctly, go to your EC2 public DNS or IP address from the browser on your local machine. The Nginx webpage should be visible.**

2.  **Configure Gunicorn on the instance:**  
    Create a systemd service file for Gunicorn, pointing it to your Django project directory.
    ```sh
    sudo nano /etc/systemd/system/gunicorn.service
    ```
    Add the following content to the file and save it *(adjust paths as per requirement)*.
    ```ini
    [Unit]
    Description=gunicorn daemon
    After=network.target

    [Service]
    User=ec2-user
    Group=nginx
    WorkingDirectory=/home/ec2-user/base_solution/subscription-management/subscription-management
    ExecStart=/home/ec2-user/base_solution/subscription-management/subscription-management/venv/bin/gunicorn \
            --access-logfile - \
            --workers 3 \
            --bind unix:/home/ec2-user/base_solution/subscription-management/subscription-management.sock \
            backend.wsgi:application

    [Install]
    WantedBy=multi-user.target
    ```
    Reload the systemd manager configuration, start the Gunicorn service, and enable it to start on boot:
    ```sh
    sudo systemctl daemon-reload
    ```
    ```sh
    sudo systemctl start gunicorn
    ```
    ```sh
    sudo systemctl enable gunicorn
    ```

3.  **Configure Nginx to act as a reverse proxy for Gunicorn**:  
    Edit the Nginx configuration:
    ```sh
    sudo nano /etc/nginx/nginx.conf
    ```
    Add the following block inside the http {} section (replace `instance-public-dns-address` with your instance public DNS or IP address):
    ```nginx
    server {
        listen 80;
        server_name instance-public-dns-address;

        location /static/ {
            alias /home/ec2-user/base_solution/subscription-management/subscription-management/static/;
        }

        location / {
            proxy_pass http://unix:/home/ec2-user/base_solution/subscription-management/subscription-management.sock;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    ```
    Check for any syntax errors:
    ```sh
    sudo nginx -t
    ```
    Restart Nginx:
    ```sh
    sudo systemctl restart nginx
    ```

### Instructions for fixing Nginx connection issue
Check Nginx error logs:
```sh
sudo tail -f /var/log/nginx/error.log
```

If you encounter this issue: `nginx connet to .sock failed (13:Permission denied) - 502 bad gateway`, follow the steps below to fix it *([forum link](https://forum.nginx.org/read.php?11,290332) for reference)*

1.  Change the default user in the very top section of the nginx.conf file to your username (`ec2-user` in this case):
    ```sh
    sudo nano /etc/nginx/nginx.conf
    ```
    Replace the default user in the file from `user nginx;` to `user ec2-user`.

2.  Toggle the SELinux boolean value for httpd network connect to on, with the persistant flag:
    ```sh
    sudo setsebool httpd_can_network_connect on -P
    ```

3.  If the issue persists after restarting Nginx and Gunicorn, recommended steps in fixing SELinux *(as per the forum)*:
    ```sh
    sudo cat /var/log/audit/audit.log | grep nginx | grep denied | audit2allow -M mynginx
    ```
    ```sh
    sudo semodule -i mynginx.pp
    ```

4.  Restart Nginx and Gunicorn services:
    ```sh
    sudo systemctl restart gunicorn
    ```
    ```sh
    sudo systemctl restart nginx
    ```

### Accessing the API and Django Admin Panel
The API would be accessible at: http://instance-public-dns-address/api/  
The Django admin panel would be accessible at: http://instance-public-dns-address/admin/  

**Steps to create an admin account for the panel (for login)**
1.  Navigate to the Django project directory in the instance:
    ```sh
    cd base_solution/subscription-management/subscription-management
    ```

2.  Activate the virtual environment:
    ```sh
    source venv/bin/activate
    ```

3.  Run the following command and enter required username and password to create the superuser to access the admin panel.
    ```sh
    python3.11 manage.py createsuperuser
    ```
Access the admin panel through the entered credentials.
