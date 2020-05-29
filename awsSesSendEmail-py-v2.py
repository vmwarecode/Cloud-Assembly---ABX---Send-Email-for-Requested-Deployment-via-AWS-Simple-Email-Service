#--------------------------------------------------------#
#                     Spas Kaloferov                     #
#                   www.kaloferov.com                    #
# bit.ly/The-Twitter      Social     bit.ly/The-LinkedIn #
# bit.ly/The-Gitlab        Git         bit.ly/The-Github #
# bit.ly/The-BSD         License          bit.ly/The-GNU #
#--------------------------------------------------------#

  #
  #       VMware Cloud Assembly ABX Code Sample          
  #
  # [Description] 
  #   - Sends email for requested deployments using AWS Simple Email Service (SES):
  #      - Request sender is notified in to
  #      - Can set static CC or BCC email in action inputs
  # [Inputs]
  #   - awsSesRegionIn (String): AWS SES region (e.g. us-west-2)
  #   - awsSesSenderIn (String): AWS SES Sender email. (e.g. no-reply@mydomain.com)
  #   - awsSesCcRecipientIn (String): CC Recipient email. (e.g. project-managers@mydomain.com)
  #   - awsSesBccRecipientIn (String): BCC Recipient email.  (e.g. managers@mydomain.com)
  #   - awsSesConfigurationSetIn (String): AWS SES configuration set name. 
  #   - actionOptionAcceptPayloadInputIn (Boolean): Can be used to turn off payload inputs and use action inputs to speed up ABX action testing. 
  #      - True: Accept payload inputs. 
  #      - False: Accept only action inputs. Mainly for ABX testing only 
  #         - runOnPorpertyMatchABXIn: see below
  #         - deploymentIdABXIn (String): Assembly Deployment ID
  #         - awsSesToRecipientABXIn (String): TO recipient email
  #   - actionOptionRunOnPropertyIn (Boolean): RunOn custom property condition
  #      - True: Check for runOn condition
  #         - runOnPropertyIn (String): Custom property key/value to match for when actionOptionRunOnPropertyIn=True ( e.g. cloudZoneProp: cas.cloud.zone.type:aws )
  #         - runOnPorpertyMatchABXIn (String): Custom property key/value to match actionOptionRunOnPropertyIn=True and actionOptionAcceptPayloadInputIn=False. For ABX testing. ( e.g. cloudZoneProp: cas.cloud.zone.type:aws )
  #      - False: Do not check for runOn condition
  #   - actionOptionRunOnBlueprintOptionIn (Boolean): RunOn blueprint option condition
  #      - True: Check for runOn condition
  #         - runOnBlueprintOptionIn (String): Blueprint property key/value to match for when actionOptionRunOnBlueprintOptionIn=True (e.g. gitlabSyncEnable: true)
  #         - runOnBlueprintOptionMatchABXIn (String): Blueprint property key/value to match for when actionOptionRunOnBlueprintOptionIn=True and actionOptionAcceptPayloadInputIn=False. For ABX testing. (e.g. gitlabSyncEnable: true)
  #      - False: Do not check for runOn condition
  #   - actionOptionUseAwsSecretsManagerIn (Boolean): Allows use of AWS Secrets Manager for secrets retrieval 
  #      - True: Use AWS Secrets Manager for secrets
  #         - awsSmRegionNameIn (String): AWS Secrets Manager Region Name e.g. us-west-2
  #         - awsSmCspTokenSecretIdIn (String): AWS Secrets Manager CSP Token Secret ID
  #      - False: Use action inputs for secrets
  #         - cspRefreshTokenIn (String): CSP Token
  # [Dependency]
  #   - Requires: pyyaml, boto3, requests
  # [Subscription]
  #   - Event Topics: deployment.request.post 
  #      - Condition: event.eventTopicId == 'deployment.request.post' && event.eventType == 'CREATE_DEPLOYMENT'
  # [Blueprint Options]
  #   - Supported options: 
  #      - awsSesEmailEnable (Boolean): Enable AWS SES notification
  #   - For more on blueprint options , visit: Using Blueprint Options in Cloud Assembly (http://kaloferov.com/blog/skkb1051/)
  # [Thanks]


import json
import requests
import yaml 
import urllib3
import boto3
from botocore.exceptions import ClientError


# ----- Global ----- #  

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)   # Warned when making an unverified HTTPS request.
urllib3.disable_warnings(urllib3.exceptions.DependencyWarning)   # Warned when an attempt is made to import a module with missing optional dependencies. 
cspBaseApiUrl = "https://api.mgmt.cloud.vmware.com"    # CSP portal base url


# ----- Functions  ----- # 

def handler(context, inputs):      # Action entry function.

    fn = "handler -"    # Funciton name 
    print("[ABX] "+fn+" Action started.")
    print("[ABX] "+fn+" Function started.")
    

    # ----- Action Options  ----- # 
    
    # General action options 
    actionOptionAcceptPayloadInput = inputs['actionOptionAcceptPayloadInputIn'].lower()     
    actionOptionRunOnProperty = inputs['actionOptionRunOnPropertyIn'].lower()   
    actionOptionRunOnBlueprintOption = inputs['actionOptionRunOnBlueprintOptionIn'].lower()
    actionOptionUseAwsSecretsManager = inputs['actionOptionUseAwsSecretsManagerIn'].lower() 
    awsSmCspTokenSecretId = inputs['awsSmCspTokenSecretIdIn']   # TODO: Set in actin inputs if actionOptionUseAwsSecretsManagerIn=True  
    awsSmRegionName = inputs['awsSmRegionNameIn']   # TODO: Set in actin inputs if actionOptionUseAwsSecretsManagerIn=True    
    runOnProperty = inputs['runOnPropertyIn'].replace('"','').lower()   # TODO: Set in actin inputs if actionOptionRunOnPropertyIn=True  
    runOnPorpertyMatch = inputs['runOnPorpertyMatchABXIn'].replace('"','').lower()    # TODO: Set in actin inputs if actionOptionAcceptPayloadInput=False  
    runOnBlueprintOption = inputs['runOnBlueprintOptionIn'].replace('"','').lower()    # TODO: Set in actin inputs if actionOptionRunOnBlueprintOptionIn=True  
    runOnBlueprintOptionMatch = inputs['runOnBlueprintOptionMatchABXIn'].replace('"','').lower()    # TODO: Set in actin inputs if actionOptionAcceptPayloadInput=False  
    cspRefreshToken = inputs['cspRefreshTokenIn']    # TODO: Set in actin inputs if actionOptionUseAwsSecretsManagerIn=False 
    blueprintId = ""    # TODO: Used to get the blueprint options 
    eventTopicId = ""   # Event Topic for which the aciton is running

    # ----- Inputs  ----- # 

    # AWS SES Inputs
    awsSesSender = inputs['awsSesSenderIn']    # Replace sender@example.com with your "From" address. This address must be verified with Amazon SES.
    awsSesToRecipient = inputs['awsSesToRecipientABXIn']    
    awsSesCcRecipient = inputs['awsSesCcRecipientIn']   # "CC" recipient address(es). 
    awsSesBccRecipient = inputs['awsSesBccRecipientIn']    # "BCC" recipient address(es). 
    deploymentId = inputs['deploymentIdABXIn']
    deploymentUrl = ""  # Deployment base url
    awsSesConfigurationSet = inputs['awsSesConfigurationSetIn']      # Specify a configuration set. If you do not want to use a configuration set, comment the following variable, and the ConfigurationSetName=CONFIGURATION_SET argument below.
    awsSesRegion = inputs['awsSesRegionIn']     # If necessary, replace us-west-2 with the AWS Region you're using for Amazon SES.
    awsSesSubject = "Cloud Assembly - Deployment completed"    # The subject line for the email.

    # eventTopicId 
    if (str(inputs).count('deployment.request.post') == 1):
        eventTopicId = "deployment.request.post"
    elif (str(inputs).count("eventTopicId") == 0):
        eventTopicId = "TEST"
    else:
        eventTopicId = "UNSUPPORTED"
    # End Loop

    # actionInputs Hashtable 
    actionInputs = {}  
    actionInputs['actionOptionAcceptPayloadInput'] = actionOptionAcceptPayloadInput
    actionInputs['actionOptionRunOnProperty'] = actionOptionRunOnProperty
    actionInputs['actionOptionRunOnBlueprintOption'] = actionOptionRunOnBlueprintOption
    actionInputs['actionOptionUseAwsSecretsManager'] = actionOptionUseAwsSecretsManager
    actionInputs['awsSmCspTokenSecretId'] = awsSmCspTokenSecretId 
    actionInputs['awsSmRegionName'] = awsSmRegionName 
    actionInputs['runOnProperty'] = runOnProperty 
    actionInputs['runOnBlueprintOption'] = runOnBlueprintOption
    actionInputs['cspRefreshToken'] = cspRefreshToken
    actionInputs['eventTopicId'] = eventTopicId
    actionInputs['awsSesSender'] = awsSesSender
    actionInputs['awsSesConfigurationSet'] = awsSesConfigurationSet
    actionInputs['awsSesRegion'] = awsSesRegion
    actionInputs['awsSesSubject'] = awsSesSubject

    # replace any emptry , optional, "" or '' inputs with empty value 
    for key, value in actionInputs.items(): 
        if (("Optional".lower() in str(value).lower()) or ("empty".lower() in str(value).lower()) or ('""' in str(value).lower())  or ("''" in str(value).lower())):
            actionInputs[key] = ""
        else:
            print('')
    # End Loop


    # Run AWS SM and GCP only when required
    if (actionInputs['actionOptionRunOnBlueprintOption'] == "true"):
    
        # ----- AWS Secrets Manager  ----- #     
        
        # Get AWS Secrets Manager Secrets
        if (actionInputs['actionOptionUseAwsSecretsManager'] == "true"):
            print("[ABX] "+fn+" Auth/Secrets source: AWS Secrets Manager")
            awsRegionName = awsSmRegionName
            awsSecretId_csp = awsSmCspTokenSecretId
            awsSecrets = awsSessionManagerGetSecret (context, inputs, awsSecretId_csp, awsRegionName)  # Call function
            cspRefreshToken = awsSecrets['awsSecret_csp']
            actionInputs['cspRefreshToken'] = cspRefreshToken
        else:
            # use action inputs
            print("[ABX] "+fn+" Auth/Secrets source: Action Inputs")

        # ----- CSP Token  ----- #     
        
        # Get Token
        getRefreshToken_apiUrl = cspBaseApiUrl + "/iaas/api/login"  # Set API URL
        body = {    # Set call body
            "refreshToken": actionInputs['cspRefreshToken']
        }
        
        print("[ABX] "+fn+" Getting CSP Bearer Token.")
        getRefreshToken_postCall = requests.post(url = getRefreshToken_apiUrl, data=json.dumps(body))   # Call 
        getRefreshToken_responseJson = json.loads(getRefreshToken_postCall.text)    # Get call response
        bearerToken = getRefreshToken_responseJson["token"]   # Set response
        requestsHeaders= {
            'Accept':'application/json',
            'Content-Type':'application/json',
            'Authorization': 'Bearer {}'.format(bearerToken),
            # 'encoding': 'utf-8'
        }
        
        actionInputs['cspBearerToken'] = bearerToken
        actionInputs['cspRequestsHeaders'] = requestsHeaders
    
    else:
        print("[ABX] "+fn+" AWS Secrets Manager and CSP Auth not required.")
    # End Loop


    if (actionInputs['actionOptionAcceptPayloadInput'] == 'true'):     # Loop. If Payload exists and Accept Payload input action option is set to True , accept payload inputs . Else except action inputs.
        print("[ABX] "+fn+" Using PAYLOAD inputs based on actionOptionAcceptPayloadInputIn action option")

        # blueprintId 
        blueprintId = inputs['blueprintId'] 
        
        # deploymentId 
        if (str(inputs).count("'deploymentId':" ) != 0):
            deploymentId = inputs['deploymentId']
        else:
            # use action inpuits 
            print('')
        # End Loop
        
        deploymentUrl = "https://www.mgmt.cloud.vmware.com/automation-ui/#/deployment-ui;ash=%2Fdeployment%2F"+deploymentId

        # awsSesToRecipient
        if (str(inputs).count("userName") != 0):
            awsSesToRecipient = inputs['__metadata']['userName']
        else:
            # Use Action inputs
            print("")
        # End Loop
        
        
        # runOn Condition Inputs
        if (actionInputs['eventTopicId'] != "TEST"):
            
            # runOnPorpertyMatch
            if (actionInputs['actionOptionRunOnProperty'] == "true"):    # Loop. Get property to match against. 
                runOnPorpertyMatch = (json.dumps(inputs)).replace('"','').lower()
            else:
                print('')
                # Get value from action inputs
            # End Loop
    
            # runOnBlueprintOptionMatch
            if (actionInputs['actionOptionRunOnBlueprintOption'] == "true"):    # Loop. Get property to match against. 
                print("[ABX] "+fn+" Using BLUEPRINT for blueprintOptions based on actionOptionRunOnBlueprintOptionIn action option")
                print("[ABX] "+fn+" Getting blueprintOptions...")
                body = {}
                resp_blueprintOptions_callUrl = cspBaseApiUrl + '/blueprint/api/blueprints/'+blueprintId+'?$select=*&apiVersion=2019-09-12'
                resp_blueprintOptions_call = requests.get(resp_blueprintOptions_callUrl, data=json.dumps(body), verify=False, headers=(actionInputs['cspRequestsHeaders']))
                #runOnBlueprintOptionMatch = str(json.loads(resp_blueprintOptions_call.text)).lower()
                runOnBlueprintOptionMatch = json.loads(resp_blueprintOptions_call.text)
                runOnBlueprintOptionMatch = yaml.safe_load(runOnBlueprintOptionMatch['content'])   # Get the BP Yaml from the Content
                runOnBlueprintOptionMatch = str(runOnBlueprintOptionMatch['options']).replace("'","").lower()    # Get the options from the BP Yaml
            else:
                print('')
                # Get value from action inputs
            # End Loop
            
        else:
            print('')
            # Get value from action inputs
        # End Loop

    elif (actionInputs['actionOptionAcceptPayloadInput'] == 'false'):
        print("[ABX] "+fn+" Using ACTION inputs for ABX action based on actionOptionAcceptPayloadInputIn action option")
        # Get values from action inputs
    else: 
        print("[ABX] "+fn+" INVALID action inputs based on actionOptionAcceptPayloadInputIn action option")
    # End Loop

    actionInputs['blueprintId'] = blueprintId
    actionInputs['deploymentUrl'] = str(deploymentUrl)
    actionInputs['deploymentId'] = deploymentId
    actionInputs['awsSesToRecipient'] = awsSesToRecipient

    actionInputs['runOnPorpertyMatch'] = runOnPorpertyMatch    
    actionInputs['runOnBlueprintOptionMatch'] = runOnBlueprintOptionMatch    
    
    # awsSesCcRecipient
    if (str(awsSesCcRecipient).count("@") == 0):
        awsSesCcRecipient = actionInputs['awsSesToRecipient']   # Use TO recipient if there are no CC
    else:
        # Use Action inputs
        print("")
    # End Loop
    
    actionInputs['awsSesCcRecipient'] = awsSesCcRecipient

    # awsSesBccRecipient
    if (str(awsSesBccRecipient).count("@") == 0):
        awsSesBccRecipient = actionInputs['awsSesToRecipient']   # Use TO recipient if there are no BCC
    else:
        # Use Action inputs
        print("")
    # End Loop

    actionInputs['awsSesBccRecipient'] = awsSesBccRecipient  

    # The email body for recipients with non-HTML email clients.
    awsSesBodyText = ("Deployment has completed.\r\n"
                "Cloud Assembly  \r\n"
                "VMware Cloud Services \r\n"
                "Spas is awesome!!!  \r\n"
                "www.kaloferov.com \r\n"
                )

    #print("[ABX] "+fn+" awsSesBodyText: " + awsSesBodyText)
    actionInputs['awsSesBodyText'] = awsSesBodyText
                
    # The HTML body of the email.
    awsSesBodyHtml = """
    <html>
    <head>
    <meta http-equiv=Content-Type content="text/html; charset=windows-1252">
    <meta name=Generator content="Microsoft Word 15 (filtered)">
    <style>
    <!--
     /* Font Definitions */
     @font-face
    	{font-family:"Cambria Math";
    	panose-1:2 4 5 3 5 4 6 3 2 4;}
    @font-face
    	{font-family:Calibri;
    	panose-1:2 15 5 2 2 2 4 3 2 4;}
    @font-face
    	{font-family:Corbel;
    	panose-1:2 11 5 3 2 2 4 2 2 4;}
    @font-face
    	{font-family:"Century Gothic";
    	panose-1:2 11 5 2 2 2 2 2 2 4;}
     /* Style Definitions */
     p.MsoNormal, li.MsoNormal, div.MsoNormal
    	{margin:0in;
    	margin-bottom:.0001pt;
    	font-size:11.0pt;
    	font-family:"Calibri",sans-serif;}
    a:link, span.MsoHyperlink
    	{color:#0563C1;
    	text-decoration:underline;}
    .MsoChpDefault
    	{font-family:"Calibri",sans-serif;}
    .MsoPapDefault
    	{margin-bottom:8.0pt;
    	line-height:107%;}
    @page WordSection1
    	{size:8.5in 11.0in;
    	margin:1.0in 1.0in 1.0in 1.0in;}
    div.WordSection1
    	{page:WordSection1;}
    -->
    </style>
    </head>
    <body lang=EN-US link="#0563C1" vlink="#954F72">
    <div class=WordSection1>
    <p class=MsoNormal><span style='font-family:"Century Gothic",sans-serif;
    color:#1E3871'>Your <a href=" """+actionInputs["deploymentUrl"]+""" ">deployment</a> has completed.</span></p><br>
    <p class=MsoNormal><b><span style='font-family:"Century Gothic",sans-serif;
    color:#1E3871'>Cloud Assembly </span></b></p><br>
    <p class=MsoNormal><b><span style='font-size:9.0pt;font-family:"Corbel",sans-serif;
    color:#0075BE'>VMware Cloud Services</span></b></p><br>
    <p class=MsoNormal><b><span style='font-size:9.0pt;font-family:"Corbel",sans-serif;
    color:#0075BE'>Spas is awesome!!! <br>
    <a href="http://www.kaloferov.com">www.kaloferov.com</a> </span></b></p>
    </div>
    </body>
    </html>

                """       
    actionInputs['awsSesBodyHtml'] = awsSesBodyHtml
    
    awsSesCharset = "UTF-8"     # The character encoding for the email.
    actionInputs['awsSesCharset'] = awsSesCharset


    # Print actionInputs
    for key, value in actionInputs.items(): 
        if (("cspRefreshToken".lower() in str(key).lower()) or ("cspBearerToken".lower() in str(key).lower()) or ("cspRequestsHeaders".lower() in str(key).lower()) or ("runOnPorpertyMatch".lower() in str(key).lower()) or ("runOnBlueprintOptionMatch".lower() in str(key).lower())):
            print("[ABX] "+fn+" actionInputs[] - "+key+": OMITED")
        else:
            print("[ABX] "+fn+" actionInputs[] - "+key+": "+str(actionInputs[key]))
    # End Loop
    
    
    # ----- Evals ----- # 
    
    evals = {}  # Holds evals values
    
    # runOnProperty eval
    if ((actionInputs['actionOptionRunOnProperty'] == "true") and (actionInputs['runOnProperty'] in actionInputs['runOnPorpertyMatch'])):   # Loop. RunOn eval.
        runOnProperty_eval = "true"
    elif ((actionInputs['actionOptionRunOnProperty'] == "true") and (actionInputs['runOnProperty'] not in actionInputs['runOnPorpertyMatch'])):
        runOnProperty_eval = "false"
    else:
        runOnProperty_eval = "Not Evaluated"
    # End Loop

    # runOnBlueprintOption  eval
    if ((actionInputs['actionOptionRunOnBlueprintOption'] == 'true') and (actionInputs['runOnBlueprintOption'] in actionInputs['runOnBlueprintOptionMatch'])):     # Loop. RunOn eval.
        runOnBlueprintOption_eval = "true"
    elif ((actionInputs['actionOptionRunOnBlueprintOption'] == 'true') and (actionInputs['runOnBlueprintOption'] not in actionInputs['runOnBlueprintOptionMatch'])):  
        runOnBlueprintOption_eval = "false"
    else:  
        runOnBlueprintOption_eval = "Not Evaluated"
    # End Loop

    evals['runOnProperty_eval'] = runOnProperty_eval.lower()
    print("[ABX] "+fn+" runOnProperty_eval: " + evals['runOnProperty_eval'])        
    evals['runOnBlueprintOption_eval'] = runOnBlueprintOption_eval.lower()
    print("[ABX] "+fn+" runOnBlueprintOption_eval: " + evals['runOnBlueprintOption_eval'])    


    # ----- Function Calls  ----- # 

    if (evals['runOnProperty_eval'] != 'false' and evals['runOnBlueprintOption_eval'] != 'false'): 
        print("[ABX] "+fn+" runOnProperty matched or actionOptionRunOnPropertyIn action option disabled.")
        print("[ABX] "+fn+" runOnBlueprintOption matched or actionOptionRunOnBlueprintOptionIn action option disabled.")
        print("[ABX] "+fn+" Running myActionFunction...")
        resp_myActionFunction = myActionFunction (context, inputs, actionInputs, evals)     # Call function
    else:
        print("[ABX] "+fn+" runOn condition(s) NOT matched. Skipping action run.")
        resp_myActionFunction = ""
     
        
    # ----- Outputs ----- #
    
    
    resp_handler = {}   # Set function response 
    resp_handler = evals
    outputs = {   # Set action outputs
       #"actionInputs": actionInputs,
       "resp_handler": resp_handler,
       "resp_myActionFunction": resp_myActionFunction,
    }
    print("[ABX] "+fn+" Function return: \n" + json.dumps(resp_handler))    # Write function responce to console  
    print("[ABX] "+fn+" Function completed.")     
    print("[ABX] "+fn+" Action return: \n" +  json.dumps(outputs))    # Write action output to console     
    print("[ABX] "+fn+" Action completed.")     
    print("[ABX] "+fn+" P.S. Spas Is Awesome !!!")

    return outputs    # Return outputs 

    
    
def myActionFunction (context, inputs, actionInputs, evals):   # Main Function. 
    fn = "myActionFunction -"    # Holds the funciton name. 
    print("[ABX] "+fn+" Action started.")
    print("[ABX] "+fn+" Function started.")
    
    
    # ----- Script ----- #

    awsSesClient = boto3.client('ses',region_name=actionInputs['awsSesRegion'])     # Create a new SES resource and specify a region.
    sendStatus = {}
    # Try to send the email.
    try:
        #Provide the contents of the email.
        send_resp = awsSesClient.send_email(
            Destination={
                'ToAddresses': [
                    actionInputs['awsSesToRecipient'],
                ],
                'CcAddresses': [
                    actionInputs['awsSesCcRecipient'],
                ],
                'BccAddresses': [
                    actionInputs['awsSesBccRecipient'],
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': actionInputs['awsSesCharset'],
                        'Data': actionInputs['awsSesBodyHtml'],
                    },
                    'Text': {
                        'Charset': actionInputs['awsSesCharset'],
                        'Data': actionInputs['awsSesBodyText'],
                    },
                },
                'Subject': {
                    'Charset': actionInputs['awsSesCharset'],
                    'Data': actionInputs['awsSesSubject'],
                },
            },
            Source=actionInputs['awsSesSender'],
            # ConfigurationSetName=actionInputs['awsSesConfigurationSet'], # TODO: Uncomment to use. Must specify via awsSesConfigurationSetIn action input
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
        sendStatus = "error"
    else:
        print("[ABX] "+fn+" Email sent!"),
        sendStatus = "ok"

        
        
    # ----- Outputs ----- #
    
    resp_myActionFunction = {}
    resp_myActionFunction = sendStatus
    
    response = {    # Set action outputs
         "send_resp": resp_myActionFunction,
    }
    print("[ABX] "+fn+" Function return: \n" + json.dumps(response))    # Write function responce to console  
    print("[ABX] "+fn+" Function completed.")   
    
    return response    # Return response 
    # End Function   
    


def awsSessionManagerGetSecret (context, inputs, awsSecretId_csp, awsRegionName):  # Retrieves AWS Secrets Manager Secrets
    # Ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/secretsmanager.html
    fn = "awsSessionManagerGetSecret -"    # Holds the funciton name. 
    print("[ABX] "+fn+" Function started.")
    
    
    # ----- Script ----- #
        
    # Create a Secrets Manager client
    print("[ABX] "+fn+" AWS Secrets Manager - Creating session...")
    session = boto3.session.Session()
    sm_client = session.client(
        service_name='secretsmanager',
        region_name=awsRegionName
    )

    # Get Secrets
    print("[ABX] "+fn+" AWS Secrets Manager - Getting secret(s)...")
    resp_awsSecret_csp = sm_client.get_secret_value(
            SecretId=awsSecretId_csp
        )

    #print(awsSecret)
    awsSecret_csp = json.dumps(resp_awsSecret_csp['SecretString']).replace(awsSecretId_csp,'').replace("\\",'').replace('"{"','').replace('"}"','').replace('":"','')   # Cleanup the response to get just the secret
    
    
    # ----- Outputs ----- #
    
    response = {   # Set action outputs
        "awsSecret_csp" : str(awsSecret_csp),
        }
    print("[ABX] "+fn+" Function completed.")  
    
    return response    # Return response 
    # End Function  
