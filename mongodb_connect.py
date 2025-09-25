import pymongo
from dotenv import load_dotenv
import os

load_dotenv()
mongodbconnection = os.getenv('MONGODB_CONNECTION_STRING')

myclient = pymongo.MongoClient(mongodbconnection)
mydb = myclient["Binary-Notes"]
newcollection = mydb["Desktop_Chatlogs"]

def insert_chatlog(chatlog):
    try:
        newcollection.insert_one(chatlog)
        print("Chatlog inserted successfully.")
    except Exception as e:
        print(f"An error occurred while inserting chatlog: {e}")