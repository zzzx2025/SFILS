import csv
import mysql.connector
import time
import sys
import argparse
import getpass

CSV_FILE = "SFPL_DataSF_library-usage_Jan_2023.csv"

def parse_bool(value): 
    if value is None:
        return None
    v = value.strip().lower()
    if v == 'true':
        return 1
    elif v == 'false':
        return 0
    else:
        return None

parser = argparse.ArgumentParser(description="Load a CSV into MySQL (small helper)")
parser.add_argument("--file", "-f", default=CSV_FILE, help="Path to CSV file")
parser.add_argument("--host", default="localhost", help="MySQL host")
parser.add_argument("--port", type=int, default=3306, help="MySQL port")
parser.add_argument("--user", default="root", help="MySQL user")
parser.add_argument("--password", "-p", help="MySQL password (omit to prompt)")
parser.add_argument("--schema", default="sfpl", help="Database/schema name to use/create")
args = parser.parse_args()

if not args.password:
    args.password = getpass.getpass(f"Password for {args.user}@{args.host}: ")

CSV_FILE = args.file
DB_HOST = args.host
DB_PORT = args.port
DB_USER = args.user
DB_PASSWORD = args.password
DB_SCHEMA = args.schema

try:
    connection = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
except Exception as e:
    print(f"error while connecting to the server: {e}")
    sys.exit(1)

if not connection or not connection.is_connected():
    print("Failed to establish a database connection. Exiting.")
    sys.exit(1)

print("successfully connected to the server\n")
cursor = connection.cursor()

start_time = time.time()
try:
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_SCHEMA}`;")
    cursor.execute(f"USE `{DB_SCHEMA}`;")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PATRONTYPES (
        Patron_Type_Definition VARCHAR(50) PRIMARY KEY
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS AGERANGES (
        Age_Range VARCHAR(50) PRIMARY KEY
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS LIBRARIES (
        Home_Library_Definition VARCHAR(100) PRIMARY KEY
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS NOTICES (
        Notice_Preference_Definition VARCHAR(50) PRIMARY KEY
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PATRONS (
        Patron_ID INT AUTO_INCREMENT PRIMARY KEY,

        Patron_Type_Code VARCHAR(20),                -- CSV col 0
        Patron_Type_Definition VARCHAR(50) NOT NULL, -- CSV col 1

        Total_Checkouts INT,                         -- CSV col 2
        Total_Renewals INT,                          -- CSV col 3

        Age_Range VARCHAR(50),                       -- CSV col 4

        Home_Library_Code VARCHAR(20),               -- CSV col 5
        Home_Library_Definition VARCHAR(100) NOT NULL, -- CSV col 6

        Circulation_Active_Month VARCHAR(20),        -- CSV col 7
        Circulation_Active_Year VARCHAR(10),         -- CSV col 8

        Notification_Preference_Code VARCHAR(20),    -- CSV col 9
        Notice_Preference_Definition VARCHAR(50),    -- CSV col 10

        Provided_Email_Address BOOLEAN,              -- CSV col 11
        Within_San_Francisco_County BOOLEAN,         -- CSV col 12
        Year_Patron_Registered VARCHAR(10),          -- CSV col 13

        FOREIGN KEY (Patron_Type_Definition)
            REFERENCES PATRONTYPES(Patron_Type_Definition),
        FOREIGN KEY (Age_Range)
            REFERENCES AGERANGES(Age_Range),
        FOREIGN KEY (Home_Library_Definition)
            REFERENCES LIBRARIES(Home_Library_Definition),
        FOREIGN KEY (Notice_Preference_Definition)
            REFERENCES NOTICES(Notice_Preference_Definition)
    );
    ''')

    patron_types = set()
    age_ranges = set()
    libraries = set()
    notices = set()
    rows = []

    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)

        next(reader, None)
        header = next(reader, None)

        columns = [
            'Patron_Type_Code',             # 0
            'Patron_Type_Definition',       # 1
            'Total_Checkouts',              # 2
            'Total_Renewals',               # 3
            'Age_Range',                    # 4
            'Home_Library_Code',            # 5
            'Home_Library_Definition',      # 6
            'Circulation_Active_Month',     # 7
            'Circulation_Active_Year',      # 8
            'Notification_Preference_Code', # 9
            'Notice_Preference_Definition', # 10
            'Provided_Email_Address',       # 11
            'Within_San_Francisco_County',  # 12
            'Year_Patron_Registered'        # 13
        ]

        query = 'INSERT INTO PATRONS ({0}) VALUES ({1})'.format(
            ','.join(f'`{c}`' for c in columns),
            ','.join(['%s'] * len(columns))
        )

        print("importing, please wait...\n")

        for data in reader:
            if not data or not any(cell.strip() for cell in data):
                continue

            def g(i):
                return data[i].strip() if i < len(data) and data[i] is not None else ""

            patron_type_code = g(0)
            patron_type_def  = g(1)

            total_checkouts = None
            if g(2):
                try:
                    total_checkouts = int(g(2))
                except ValueError:
                    total_checkouts = None

            total_renewals = None
            if g(3):
                try:
                    total_renewals = int(g(3))
                except ValueError:
                    total_renewals = None

            raw_age = g(4)
            age_range = raw_age if raw_age else None

            home_lib_code = g(5)
            home_lib_def  = g(6)

            circ_month = g(7)
            circ_year  = g(8)

            notif_pref_code = g(9)
            notice_pref_def = g(10)

            provided_email = parse_bool(g(11))
            within_sf      = parse_bool(g(12))
            year_reg       = g(13)

            if patron_type_def:
                patron_types.add(patron_type_def)
            if age_range is not None:
                age_ranges.add(age_range)
            if home_lib_def:
                libraries.add(home_lib_def)
            if notice_pref_def:
                notices.add(notice_pref_def)

            row = [
                patron_type_code,
                patron_type_def,
                total_checkouts,
                total_renewals,
                age_range,
                home_lib_code,
                home_lib_def,
                circ_month,
                circ_year,
                notif_pref_code,
                notice_pref_def,
                provided_email,
                within_sf,
                year_reg
            ]
            rows.append(row)

    for p in patron_types:
        cursor.execute(
            "INSERT IGNORE INTO PATRONTYPES (Patron_Type_Definition) VALUES (%s)",
            (p,)
        )
    for a in age_ranges:
        cursor.execute(
            "INSERT IGNORE INTO AGERANGES (Age_Range) VALUES (%s)",
            (a,)
        )
    for l in libraries:
        cursor.execute(
            "INSERT IGNORE INTO LIBRARIES (Home_Library_Definition) VALUES (%s)",
            (l,)
        )
    for n in notices:
        cursor.execute(
            "INSERT IGNORE INTO NOTICES (Notice_Preference_Definition) VALUES (%s)",
            (n,)
        )

    connection.commit()

    for data in rows:
        cursor.execute(query, data)
    connection.commit()

    end_time = time.time()
    duration = end_time - start_time
    print(f"CSV successfully converted in {duration:.3f} seconds! exiting...\n")

except Exception as e:
    print(f"error during DB operations: {e}")
    try:
        connection.rollback()
    except Exception:
        pass
finally:
    try:
        if cursor:
            cursor.close()
    except NameError:
        pass
    try:
        if connection and connection.is_connected():
            connection.close()
    except NameError:
        pass
