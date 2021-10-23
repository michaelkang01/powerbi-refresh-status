from getopt import getopt, GetoptError
import sys
from os import environ
import yaml
from datetime import datetime, timedelta
import pandas as pd

from datadog import initialize, statsd

from lib.qtlogger import getLogger
from lib.lib import get_token, who_i_am
from refreshes import _get_schedule, _get_history
from lib.bigquery import write_bigquery

# datadog client init
LOCALHOST = '127.0.0.1'
datadog_host = environ.get('DD_AGENT_HOST', LOCALHOST)
datadog_port = environ.get('DD_AGENT_PORT', 8125)

config = {'statsd_host': datadog_host,
          'statsd_port': datadog_port,
          'hostname_from_config': False}

initialize(**config)
# ----------------------
def load_local_variables():

    logger.debug('Loading local variables to support local run')
    with open('cfg/local_run_env.yaml', 'r') as f:
        file = f.read()
        config = yaml.safe_load(file)
    environ[f'{company}_client_username'] = config[f'{company}_client_username']
    environ[f'{company}_client_password'] = config[f'{company}_client_password']
    environ[f'{company}_client_id'] = config[f'{company}_client_id']


logger = getLogger(source='PowerBI refreshes')

# switch off error stack in output
#logger.exception_enabled = False

# allowed companies
COMPANIES = ['questrade', 'ctc']

# processed rows. To keep up statistics...
rows_processed=0
# parse arguments and decide on a plan (if not a local run):
if 'local_run' in environ:
    env = 'sit'
    company = 'ctc'
    logger.debug('RUNNING LOCAL!!!!')
    try:  # load some sensitive variables from a local config file
        load_local_variables()
    except FileNotFoundError as ex:
        logger.error(ex)
        exit(8)
    except Exception as ex:
        logger.error(f'Parameter {ex} not found in the cfg/local_run_env.yaml config file')
        exit(6)
else:
    args = sys.argv[1:]
    logger.info(f'Arguments passed: {sys.argv}')
    try:
        opts, aux = getopt(args, '', ['company='])
    except GetoptError as ex:
        logger.error(f'Error: {ex}. Only one command-line option --company is allowed')
        exit(4)
    if len(opts) == 0 \
            or opts[0][0] != '--company' \
            or opts[0][1] not in COMPANIES:
        logger.error(f'Error. Parameter --company has wrong value or not defined')
        exit(1)
    company = opts[0][1]
    # environment:
    env = environ.get('ENV', 'sit')

logger_level = 'DEBUG' if env == 'sit' else 'INFO'
logger.setLevel(logger_level)

def get_config(company):
    # load configuration
    with open(f'./cfg/config-{env}.yaml', 'r') as f:
        file = f.read()
        config = yaml.safe_load(file)[company]
    return config


def get_refreshes(company, **cfg):

    global rows_processed

    # initializing return variables
    logger.info(f'Getting refresh information for {company}. Environment:{env}')
    # grab our configuration
    config = cfg['parameters']
    # Set up all of our variables so that we can retrieve the auth token
    try:
        authority_url = config['authority_url']
        resource = config['resource']
        username = environ[f'{company}_client_username']
        password = environ[f'{company}_client_password']
        client_id = environ[f'{company}_client_id']
        token = get_token(authority_url, resource, username, password, client_id)
    except KeyError as ex:
        logger.error(f'Key {ex} was not found in the configuration')
        exit(2)
    except Exception as ex:
        logger.error(f'Cannot obtain security token: {ex}')
        exit(2)

    #Send RefreshHistory Data
    logger.info(f'Getting refresh history information for {company}. Environment:{env}')
    dsh = _get_history(company, token)
    #Send RefreshSchedule Data
    logger.info(f'Getting refresh schedules information for {company}. Environment:{env}')
    dss = _get_schedule(company, token)
    datasets = []
    datasets.append(dss[0])
    datasets.append(dsh[0])
    logger.info(f'Writing to BigQuery')
    for i in (0, len(datasets) - 1):
        dds = pd.DataFrame(datasets[i]["Dataset"])
        if dds.shape[0] > 0:
            results = write_bigquery(dataset=datasets, parameters=config)
            rows_processed += results[0]['Rows processed']



def main():
    global env, company
    if not company:  # company is not defined
        logger.error('Error: please define company in the command-line parameter --company')
        exit(1)

    # read configuration for company
    try:
        config = get_config(company)
    except Exception as ex:
        logger.error(f'Error: {ex}')
        exit(255)
    
    #run our command
    get_refreshes(company, parameters = config)
    
    logger.info("Done")


if __name__ == '__main__':
    try:
        # store runtime
        starttime = datetime.now()
        # run
        main()

        endtime = datetime.now()
        duration = (endtime - starttime).seconds
        statsd.histogram('etl_duration', duration,
                         tags=[f'product:PowerBI Data Collector', f'etl:PowerBI-Refreshes-{company}'])
        statsd.histogram('etl_rows_processed', rows_processed,
                         tags=[f'product:PowerBI Data Collector', f'etl:PowerBI-Refreshes-{company}'])

    except Exception as ex:
        logger.error(ex)
        exit(1001)


