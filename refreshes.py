from lib.lib import who_i_am, API
import pandas as pd
import numpy as np
from time import sleep
from datetime import datetime
from datetime import timedelta

NUM_RETRIES = 5  # number of API call attempts before it returns hard fail
DELAY_RETRIES = 0.5  # delay in seconds between API call retries in case there is a temporary network issue

def _get_datasetsAsAdmin(company, token):
    """Helper function that returns the 'value' list of datasetes
    as given in the PowerBI REST API documentation.

    company = (string)
    token = (string)
    Returns: (List of Dicts)
    """
    #Setting up
    api = API()
    api.add_header('Authorization', "Bearer " + token)
    datasets = []
    #Local vars to retry
    retries = NUM_RETRIES
    #convert from JSON to Python notation !!! Find better solution
    true = True
    false = False
    #Get all of the data sets
    url = "https://api.powerbi.com/v1.0/myorg/admin/datasets"
    while retries > 0:
        responseDatasets = api.get(url)
        if responseDatasets.status_code == 200:
            datasets = responseDatasets.json().get('value')
            return datasets
        retries -=1
        if retries == 0:
            raise ValueError(f'Data has been recieved partially. {responseDatasets.status_code}:{responseDatasets.reason}')
        sleep(DELAY_RETRIES)
    #If empty then did not work as intended
    return datasets

def _get_runtime(company, token, startTime, endTime):
    """Helper function that retrieves the runtime of a
    refresh event
    company=(string)
    token=(string) 
    startTime=(string) #in form 2017-06-13T09:31:43.153Z
    endTime=(string) # in form 2017-06-13T09:31:43.153Z
    """
    startTime = startTime.rstrip(startTime[-1])
    endTime = endTime.rstrip(endTime[-1])
    start = startTime.split("T")
    end = endTime.split("T")
    nomilisStart = start[1].split(".")
    nomilisEnd = end[1].split(".")
    #Use datetime to solve for date.
    FMT = "%H:%M:%S"
    tdelta = datetime.strptime(nomilisEnd[0], FMT) - datetime.strptime(nomilisStart[0], FMT)
    if tdelta.days < 0:
        tdelta = timedelta(days=0, seconds=tdelta.seconds, microseconds=tdelta.microseconds)
    return tdelta.seconds + tdelta.microseconds * 1000000

def _get_schedule(company, token):
    """ Returns the Name and a pandas DataFrame in a Dictionary.
        The DataFrame contains DataSet information of all DataSets that are
        set to refresh on schedule, as well as their corresponding schedules,
        taken from PowerBI's REST API.
        
        company=(string)
        token=(string) #authentication token
        Returns: dataset=['Name':(string), 'Dataset': pandas.DataFrame]
    """
    #Initialize API
    api = API()
    api.add_header('Authorization', "Bearer " + token)
    dataset = []
    #Set up our final dataframe
    pdrefs = pd.DataFrame()
    #Local copy of retry attempts.
    retries = NUM_RETRIES
    #Use these to convert JSON bool to Python Bool
        #!!!! FIND A BETTER SOLUTION EVENTUALLY
    true = True
    false = False
    datasets = _get_datasetsAsAdmin(company, token)
    for item in datasets:
        #We only want to consider datasets that can get refreshed (to REST API that means model-based datasets)
        if item['isRefreshable'] == true:
            #if you want any of the other dataset data, you can add them to this DataFrame
            #View the documentation here https://docs.microsoft.com/en-us/rest/api/power-bi/datasets/getdatasets
            pdds = pd.DataFrame({'DatasetID': [item['id']], 'DatasetName': [item['name']], 'DatasetConfiguredBy': [item['configuredBy']]})
            #get the URL for the dataset's refresh schedule
            refURL = f'https://api.powerbi.com/v1.0/myorg/admin/datasets/{item["id"]}/refreshSchedule'
            #Get the refresh schedule of the dataset
            #Check for database refresh status
            while retries > 0:
                refResponse = api.get(refURL)
                if refResponse.status_code == 404:
                    break
                if refResponse.status_code == 200:
                    #get the data of the refresh schedule
                    refs = refResponse.json()
                    #If you want to get ONLY the schedules of datasets that have enabled = true
                    """if refs.get('enabled') == false:
                        break;
                    """
                    #Make a block for each day.
                    for day in refs.get('days'):
                        #Make an entry for each time
                        for time in refs.get('times'):
                            pdtemp = pd.concat([pdds, pd.DataFrame({'Day':[day], 'Time':[time], 'TimeZone': [ refs.get('localTimeZoneId')], 'Enabled':[refs.get('enabled')]})], axis=1)
                            pdrefs = pdrefs.append(pdtemp, ignore_index=True)
                    break
                #check for getting schedules
                retries -= 1
                if retries == 0:
                    raise ValueError (f'Data has been received partially. {refResponse.status_code}:{refResponse.reason}')
                sleep(DELAY_RETRIES)
    #Proper format by replacing nan with None
    pdrefs = pdrefs.replace({np.nan: None})
    dataset.append({'Name': "refreshschedules", 'Dataset': pdrefs})
    return dataset
    
#Similar to above but gets the histories instead.
def _get_history(company, token):
    """ Returns the Name and a pandas DataFrame in a Dictionary.
        The DataFrame contains DataSet information of all DataSets that have
        a refresh history and their entire histories. Taken from PowerBI's
        REST API.
        
        company=(string)
        token=(string) #authentication token
        Returns: dataset=['Name':(string), 'Dataset': pandas.DataFrame]
    """
    #Initialize API
    api = API()
    api.add_header('Authorization', "Bearer " + token)
    dataset = []
    pdrefh = pd.DataFrame()
    #Local copy of retry attempts.
    retries = NUM_RETRIES
    #Use these to convert JSON bool to Python Bool
        #!!!! FIND A BETTER SOLUTION EVENTUALLY
    true = True
    false = False
    datasets = _get_datasetsAsAdmin(company, token)
    for item in datasets:
        #We only want to consider datasets that can get refreshed (to REST API that means model-based datasets)
        if item['isRefreshable'] == true:
            #if you want any of the other dataset data, you can add them to this DataFrame
            #View the documentation here https://docs.microsoft.com/en-us/rest/api/power-bi/admin/datasets_getdatasetsasadmin
            pdds = pd.DataFrame({'DatasetID': [item['id']], 'DatasetName': [item['name']], 'DatasetConfiguredBy': [item['configuredBy']]})
            #get the URL for the dataset's refresh schedule
            refURL = f'https://api.powerbi.com/v1.0/myorg/admin/datasets/{item["id"]}/refreshes'
            #Get the refresh schedule of the dataset
            #Check for database refresh status
            while retries > 0:
                refResponse = api.get(refURL)
                if refResponse.status_code == 404:
                    break;
                if refResponse.status_code == 200:
                    #get the data of the refresh schedule
                    refh = refResponse.json().get('value')
                    #for every entry in the refresh history, we add an entry to data.
                    #Note if the dataset never refreshes, it will always have empty entries here.
                    for entry in refh:
                        pdtemp = pd.concat([pdds, pd.DataFrame([entry])], axis = 1)
                        #Calculate the runtime if we have start/endtimes (completed or failed)
                        if entry["status"] == "Failed" or entry["status"] == "Completed":
                            runtime = _get_runtime(company, token, entry["startTime"], entry["endTime"])
                            pdtemp = pd.concat([pdtemp, pd.DataFrame({"RuntimeSeconds": [runtime]})], axis=1)
                        pdrefh = pdrefh.append(pdtemp, ignore_index=True)
                    break
                #check for getting history
                retries -= 1
                if retries == 0:
                    raise ValueError (f'Data has been received partially. {refResponse.status_code}:{refResponse.reason}')
                sleep(DELAY_RETRIES)
    #Proper format by replacing nan with None
    pdrefh = pdrefh.replace({np.nan: None})
    dataset.append({'Name': "refreshhistory", 'Dataset': pdrefh})
    return dataset