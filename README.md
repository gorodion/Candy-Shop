# Candy-Shop
Rest-api for handling delivery requests. Written on Flask with MySQL database connection
# Instruction
In bash shell run the following commands:
```
sudo apt-get update
sudo apt-get install python3.9
sudo apt-get install python3.9-venv
sudo apt-get install python3-pip
sudo python3.9 -m pip install -U pip
sudo python3.9 -m pip install -r requirements.txt
sudo apt-get install mysql-server
sudo mysql
```
After that in MySQL command-line:
```sql
CREATE USER 'YOUR_USER'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON *.* TO 'YOUR_USER'@'localhost';
CREATE DATABASE DATABASE_NAME
SOURCE database/candy.sql
```
Create file **config.py** with the following content:
```python
DB_HOST = 'YOUR_HOST'
DB_USER = 'YOUR_USER'
DB_PASSWORD = 'YOUR_PASSWORD'
DB_DATABASE = 'YOUR_DATABASE'
```
And finally run script:
```
sudo python3.9 app.py
```
