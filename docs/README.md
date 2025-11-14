# Project Documentation

To begin getting the excel table data into the MySQL database, we want to make sure it is in a csv file. If it is not in a csv file, save the xlsx file as a csv file. 

We can try to import the csv data into MySQL Workbench and check if the data have been imported correctly. In my case, it didn't import the data, so I created a code to import it into MySQL. This can be verify on MySQL Workbench by pressing the refreshing button by the SCHEMA.

<img width="402" height="27" alt="image" src="https://github.com/user-attachments/assets/756fffc2-aee2-43cd-a134-e11770ebc42f" />

Once the data is created in MySQL and verify, we create the stuff we need to be able to run the user interface python app. We create a requirements text file for the applications/libraries we need to download, and a .env file for us to be able to access MySQL database.

The requirements.txt file have the following:
steamlit
mysql-connector-python
pandas
oython-dotenv

The .env file have the following:
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=password
DB_NAME=name

The password should be your password for MySQL and the name should be the name of your database in MySQL.

Create and activate the virtual enviroment to run the app UI. Must already have python install and use the terminal to create the venv and activate. Use the terminal to install the requirements applications/libraries and run the app.
Command to create:
python -m venv .venv

Command to activate for Windows (different if using macOS or Linux):
.venv\Scripts\activate

Commands to install the requirements:
pip install -r requirements.txt

Command to run app UI (the python app file is named app.py):
streamlit run app.py

# app.py
(Continue later)
