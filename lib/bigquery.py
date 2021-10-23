from google.cloud import bigquery
import pandas as pd
import json

from lib.lib import who_i_am


def write_bigquery(dataset, **kwargs):
    """

    :param kwargs: any of these arguments:
    :param dataset: list of datasets [{'set_name'(string) : ds (Pandas DataFrame)}]
    :return:
    """
    response=[]
    parameters = kwargs['parameters']
    bq_dataset = parameters['dataset']
    asjson = parameters.get('asjson', False)
    table = parameters.get('table', None)
    client = bigquery.Client(parameters["project"])

    bq_job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        #schema_update_options=["ALLOW_FIELD_ADDITION"] since truncate will always overwrite.
         # ,
         # schema=[
         #     bigquery.SchemaField(name="Datasets",field_type="RECORD", ),
         # ],
    )
    for item in dataset:
        if table:
            tblname = f'{bq_dataset}.{table}'
        else:
            tblname = f'{bq_dataset}.{item["Name"]}'

        if asjson:
            #The content of the json is different based on the type of the activity.
            #Due to the nature of this API request.
            value = pd.Series(item["Dataset"].to_dict(orient='records')).rename('js').apply(lambda x: json.dumps(x))
            ds = pd.DataFrame(value)
        else:
            ds = item["Dataset"]
        # TODO: add try..catch block to handle BigQuery write errors

        try:
            client.load_table_from_dataframe(ds, tblname, job_config=bq_job_config)
        except Exception as ex:
            raise ValueError(ex)

        res = {"Object": item["Name"], "Rows processed": ds.shape[0]}
        response.append(res)

    return response
