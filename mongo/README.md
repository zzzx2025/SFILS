# MISFILS
MISFILS: The MongoDB-based Implementation for the San Francisco Integrated Library System.

This folder contains the submission files for Assignment 2. The remaining folders contain the files from Assignment 1.

Make sure to keep all your Assignment 2 files inside this folder to keep the rest of the folders free from clutter. That way, it will be easier to grade both Assignment 1 and Assignment 2.

# Installation
To install MongoDB into our local computer/laptop we go to
https://www.mongodb.com/try/download/community
https://www.mongodb.com/try/download/shell
-install MongoDB shell (CLI)
https://www.mongodb.com/try/download/compass
-install MongoDB Compass (GUI)

(make sure to download the correct tools to use mongodb depending on your OS)

We want to use python for mongodb, so we will need to install pymongo
To install pymongo, we go to the terminal we are using and use command
python -m pip install pymongo (make sure it is the right python if you have multiple python install)

Since we are using the python code to upload the data into the mongodb, we will be using the same python code we used for MySQL with some changes.

We will be removing SQL table creation since mongodb doesn't create table and the rows creation. For mongodb, we will create a document for the rows. They will be inserted into mongodb using the command insert_many()

If we do not have codes for it already we can create one
First we want to import libraries we are using, such as:
csv, MongoClient, argparse, and time

Then we want the scripts to read the csv file (in the same folder), converts each row into a JSON-like Python dictionary, and insert those as documents into the MongoDB. The argparse allow us to control which csv file to load and to what database name to use.

MongoClient allow us to connect to the mongodb to create the database and collection of the documents we insert.
When reading the csv file, we want to skip the header row and we want to get the data of each row with all the columns. These data would be put into the python dict as we insert it into the mongodb as we insert many data instead of one at a time.

After this, we would have a copy of the csv file data in the mongodb

All the patrons are stored in the sfpl.patrons collection. Each document corresponds to a row in the CSV file. Both the '_id' and 'Patron_ID' are integers and use the same value to make it easier to identify patrons. The 'Provided_Email_Address' and 'Within_San_Francisco_County' are Boolean fields that are stored as real Booleans and not strings. The 'Total_Checkout' and 'Total_Renewals' are integer fields and are stored as numbers, which can be used in comparisons and aggregations. 

# Storing and Retrieving Data
I'll be showing how to store and retrieve data from the mongodb on mongodb shell since the app is easy to use and have the same 6 functions (view all, add new, update, search, delete, and logs) we have for MySQL. On the mongodb shell, to use the database with the data, we put in the command 'use sflp' since sflp is the name of my database.

An example of using the shell to find patrons
db.patrons.find({Patron_Type_Definition: "Adult"})
<img width="582" height="1115" alt="Screenshot 2025-11-19 204224" src="https://github.com/user-attachments/assets/5795bf0f-9d07-47a9-bdfa-075cf3604e5e" />

This command will show a list of Patrons who are adults. The list show is limited on the shell, but you can type 'it' to have it show more. But you can narrow down the search by adding more, for example:
db.patrons.find({Patron_Type_Definition: "Adult", Home_Library_Definition: "Mission"})

<img width="554" height="1111" alt="Screenshot 2025-11-19 205544" src="https://github.com/user-attachments/assets/4e0426bc-70b1-47f6-a3b2-e9919a2d7d44" />

This will look for patrons who are adults and their home library is mission.

With aggregation, we can do stuff like checking the numbers of patrons by their home library
db.patrons.aggregate([{$group: {_id: "$Home_Library_Definition", patron_count: {$sum: 1}}}, {$sort: {patron_count: -1}}])

<img width="389" height="1118" alt="Screenshot 2025-11-19 211348" src="https://github.com/user-attachments/assets/c7f2e04f-b6a9-4670-8c4d-b6927b9d6d11" />


For the app, we will also be creating a virtual environment to run it. Everything we did for MySQL on the app is the same as the one for MongoDB, so nothing have change for this.

# Acknowledgement
I would like to acknowledge that Ryder helped clarified some things for me. Since this assignment is similar to assignment 1, I just needed help clarifying some of the instructions, I tend to confuse myself sometimes.
