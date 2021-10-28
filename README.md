# Power BI Refreshes


[Error codes](#error-codes)
## Release history

| Version   | Date          | 
| ----      | ----          |
| 0.1       | Jun. 24, 2021 |

------

## General information  

`PowerBI Collector` uses Microsoft [PowerBI API](https://docs.microsoft.com/en-us/rest/api/power-bi/) to interact with PowerBI Web Service.  

Currently, `PowerBI Collector` supports:  
* Gathering of usage statistics 
* Assets inventory (list of workspaces, datasets, reports, users)
* Dataset refresh schedules and history
* BigQuery as the only destination
* Collecting data for multiple tenants/companies

In next releases, we are going to add:  
* Datasets refresh retry functionality
* CloudSQL support

## Pre-requisites
To start using PowerBI API, it is required to register an `Azure Active Directory application` (in `Embed for the organization` mode).  
Check [here](https://docs.microsoft.com/en-us/power-bi/developer/embedded/register-app?tabs=organization%2CAzure) for more details on how register application.  
Once the application is registered, you should have an `ApplicationID`. See [Vault](#Vault) section for further details.

`Important`: This application have to be created for each tenant/company you want to collect data for.

## Configuration
Follow these steps to configure `PowerBI Collector`

### <font color=orange>paas.config.yaml</font>
(`./cfg` folder)  
Here is an example of the configuration file. All parameters are mandatory, but values should be adjusted appropriately.  

This example configures two cronjobs that will use the same GKE image as a base. First cronjob queries data for CTC (`--company=***` as a command-line parameter), whereas second one quieries data for *****.  

Both cronjobs are configured to run at 7.00am (UTC) daily.

```yaml
service_name: powerbi-refreshes
stack: python
owner: *             

app_deployment: false           # since runtime is build, we leave app deployment to false

cronjobs:                       # it is possible to define multiple cronjobs, and multiple run parameters. Every cronjob is running in its own pod.
  - name: powerbi-refreshes-***     # this will become a cronjob name in Google Kubernetes Enviorment (GKE)
    runtime: build      # leave as build for this project.
    schedule: "0 7 * * *"       # adjust this to adjust when the cronjob runs.
    dockerfile: Dockerfile.cronjob.powerbi-ref      # this should be the name of the dockerfile in the root directory (where main.py is found)
    args: "--company=***"       # command-line parameter for this instance
  - name: powerbi-refreshes-*****
    runtime: build
    schedule: "0 7 * * *"
    dockerfile: Dockerfile.cronjob.powerbi-ref
    args: "--company=*****"

bigquery:                       # since this job writes to BigQuery, it should be enabled
  enabled: true

rbac:
  env:
    sit:
      users:
      - **
      groups:
      - ****
```

### <font color=orange>config-xxx.yaml</font>
(`./cfg` folder)  
All non-sensitive parameters should be placed here.  
*Important*: It is possible to have a separate configuration for every environment. Use either `-sit`, `-uat`, or `-prod` as a suffix to specify target environment.

The program allows pulling data for multiple companies, so all relevant parameters should be placed under company's name:
``` yaml
ctc:        # company name
    authority_url: "https://login.microsoftonline.com/***"        # authentication url
    resource: "https://analysis.windows.net/powerbi/api"        # api endpoint target
    dataset: "pbirefreshes"     # target BigQuery dataset name
    project: "*"        # target BigQuery project name (where the dataset will be found)
    asjson: True        # True - result will be stored as a single-column json document, False - result will be stored as multicolumn table
    save_strategy: separate     # will write to tables with every write_bigquery() call according to table name provided, remove if all in one table is preferred.
questrade:
    authority_url: "https://login.microsoftonline.com/*****"
    resource: "https://analysis.windows.net/powerbi/api"
    dataset: "pbirefreshes"
    project: "*"
    asjson: True
    save_strategy: separate
```

### <font color=orange>bigquery.yaml</font>
(`.\cfg` folder)  
Contains BigQuery configuration (project, dataset, tables) for the environments. It is possible to pre-define tables structure along with extra parameters (like `partitioning`, `expiration`)  
This file is required by the pipeline to configure BigQuery instance.  

<font color=red>Important:</font> 
Configuration in the `config-xxx.yaml` file is a program configuration, whereas configuration in the `bigquery.yaml` is required by the deployment pipeline.

```yaml
bigquery:
  location: US      # server location, probably do not need to change.
  env:
    sit:        # enviorment type, could be sit, uat, prod.
      datasets:
      - name: "pbirefreshes"        # dataset name, should be the same as in config-xxx.yaml
        tables:
        - name: "refreshhistory"        # table names, should provide for each write_bigquery() call in program. If not using "seperate" configuration, should provide only one table.
        - name: "refreshschedules"

```

General information on BigQuery configuration can be found [here](*)

### <font color=orange>Vault</font>
All sensitive parameters (Username/password pairs, sensitive IDs) have to be saved in the [HashiCorp vault](*).  

For each company you want to pull data for, save these key-value pairs at *env*/powerbi-refreshes/powerbi-refreshes/secret branch:  

| key name                  | value                                                                        |
| ----                      | ----                                                                         |
|*company*_client_id        | put here ApplicationID from [Pre-requisite](#pre-requisite) section          |
|*company*_client_username  | domain service account that has at least Viewer access to PowerBI workspaces |
|*company*_client_password  | service account password                                                     |



---
## Error codes

| Code | Description| Resolution |
| ---- | :----| --- |
|1| Command line parameters are not defined, or value is out of range. Required parameter is: `--company=['*****', '***']`| Check command-line partameters
|2| Error getting PowerBI security token | Ensure you specified correct `username`, `password`, and `client-id` variables in Vault.
|3| Called function is not implemented yet | Call Data Masters team |
|4| Command-line option is not recognized. There is only one `--company` option allowed | Check command-line parameters |
|5| Error parsing command-line parameters| Check command-line parameters
|6| It was an attempt to run code locally (outside of the docker), but there is no local config file defined.|Check if `cfg/local_run_env.yaml` file exists|
|7| Security token retrieval fail | Check `username`, `password`, `client_id` parameters in Vault/local config|
|8| Configuration file not found | Check folder `cfg/` for the config file | 
