# Load libraries
from azure.storage.blob import BlobServiceClient

import pandas as pd

import os
import json
import logging
import traceback
import urllib.parse

import datetime # For testing only

import pyodbc
from sqlalchemy import create_engine

from File_1 import DataAnalysis



class Motorcade:

    def __init__(self, path_json = 'var.json'):

        self.config_path = path_json

        self.config_file = None
        self.blob_service_client = None

        self.df_duty_cycle = None
        self.df_client_fleet = None

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
    

    def load_json(self):

        try:
            with open(self.config_path, 'r') as file:
                self.config_file = json.load(file)

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            print(f"Failed to load configuration: {e}")


    def initialize_client(self):

        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(conn_str=self.config_file["on_cloud"]["conn_string_BlobStorage"])
        except Exception as e:
            self.logger.error(f"Failed to initialize blob service client: {e}")
            print(f"Failed to initialize blob service client: {e}")


    def load_dutycycle(self, connection_string):

        try:
            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()

            # Execute query
            query = "SELECT * FROM [dbo].[DutyCycles]"
            cursor.execute(query)

            columns = [field[0] for field in cursor.description]
            rows = cursor.fetchall()
            duty_cycle = [row for row in rows]
            self.df_duty_cycle = pd.DataFrame.from_records(duty_cycle, columns=columns)

        except pyodbc.Error as e:
            self.df_duty_cycle = None
            self.logger.error(f"Database error: {e}")
            print(f"Database error: {e}")


        except Exception as e:
            self.df_duty_cycle = None
            self.logger.error(f"An error other than database occurred: {e}")
            print(f"An error other than database occurred: {e}")

        finally:
            # Close the database connection
            if cursor:
                cursor.close()
            if conn:
                conn.close()


    def load_clientfleet(self, connection_string):

        try:
            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()

            # Execute query
            query = "SELECT * FROM [dbo].[ClientFleet]"
            cursor.execute(query)

            columns = [field[0] for field in cursor.description]
            rows = cursor.fetchall()
            client_fleet = [row for row in rows]
            self.df_client_fleet = pd.DataFrame.from_records(client_fleet, columns=columns)

        except pyodbc.Error as e:
            self.df_client_fleet = None
            self.logger.error(f"Database error: {e}")
            print(f"Database error: {e}")


        except Exception as e:
            self.df_client_fleet = None
            self.logger.error(f"An error other than database occurred: {e}")
            print(f"An error other than database occurred: {e}")

        finally:
            # Close the database connection
            if cursor:
                cursor.close()
            if conn:
                conn.close()




def main():

    # GET FILENAME *********************************************************************************
    with open("activity.json", "r") as file:
        activity = json.loads(file.read())
        # print(activity["typeProperties"]["extendedProperties"].keys())
        # print(activity["typeProperties"]["extendedProperties"].values())
        # print(activity["typeProperties"]["extendedProperties"])
        filename = activity["typeProperties"]["extendedProperties"]["filename"]
        granularity = int(activity["typeProperties"]["extendedProperties"]["granularity"])

    # List all files in the directory
    current_directory = os.getcwd()
    quoted_file_list = os.listdir(current_directory)
    unquoted_file_list = [urllib.parse.unquote(name) for name in quoted_file_list]
    index = unquoted_file_list.index(filename)
    filename = quoted_file_list[index]


    # GET BLOB CLIENT ***********************************************************************************
    startmotor = Motorcade()
    startmotor.load_json()          # Load the json
    startmotor.initialize_client()  # Establish connection with the blob storage account / create blob client for every blob


    # GET CLIENT DATA AND DUTY CYCLE DFs *******************************************************************
    # print(startmotor.config_file["on_cloud"]["conn_string_SQLAuth"])
    startmotor.load_dutycycle(startmotor.config_file["on_cloud"]["conn_string_SQLAuth"])
    startmotor.load_clientfleet(startmotor.config_file["on_cloud"]["conn_string_SQLAuth"])




    # DO ANALYSIS *******************************************************************************************
    df = pd.read_csv(filename)


    # # Take a subset of the records
    # df = df.iloc[:, [2,3,4]]

    # # Save the subset of the iris dataframe locally in the task node
    # df.to_csv(filename, index = False)

    # with open(filename, "rb") as data:
    #     client_blob.upload_blob(data, overwrite=True)




    # Calculate summary statistics

    try:
    
        da = DataAnalysis(df, startmotor.config_file, startmotor.df_client_fleet, startmotor.df_duty_cycle, granularity)

        keys = startmotor.config_file["columns"]["data_trip_summary"]
        values = list(da.generate())
        dictionary = {key: [value] for key, value in zip(keys, values)}
        
        # df = pd.DataFrame(dictionary, index=[0])
        df = pd.DataFrame.from_dict(dictionary)

        # Connect to SQL database
        quoted = urllib.parse.quote_plus(startmotor.config_file["on_cloud"]["conn_string_SQLAuth"])
        print(quoted)
        engine = create_engine('mssql+pyodbc:///?odbc_connect={}'.format(quoted))
        
        # Save dataframe to SQL table. Dataframe columns must match SQL fields
        df.to_sql('StatsSummary', con=engine, if_exists='append', index=False)
        startmotor.logger.info('Summary stats uploaded to database')


        # Testing only ******************************************************************************************
        current_time = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
        save_name = f"data_{current_time}.csv"
        folder_cloud_save= startmotor.config_file["on_cloud"]["containerReadyDataOutput"]
        client_blob = startmotor.blob_service_client.get_blob_client(folder_cloud_save, save_name) 

        df.to_csv(save_name, index=False) 
        with open(save_name, "rb") as data:
            client_blob.upload_blob(data, overwrite=True)
        # *********************************************************************************************************

    except Exception as e:
        startmotor.logger.error(f"Error producing trip summary stats: {e}  --- {traceback.format_exc()}")
        print(f"Error producing trip summary stats: {e}")




if __name__ == "__main__":

    main()