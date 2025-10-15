param appServicePlanName string
param backendWebAppName string
param location string
param OpenAIEndPoint string
param identityName string
param logAnalyticsWorkspaceName string
param appInsightsName string
param cosmosdbEnpoint string
param cosmosdbDatabase string ='chatdatabase'
param cosmosdbHistoryContainer string ='chathistory'
param cosmosdbFeedbackContainer string ='feedback'
param cosmosdbEvaluationContainer string



@description('Endpoint URL of the Azure Cognitive Search service (e.g., https://<service>.search.windows.net)')
param searchServiceEndpoint string


resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' existing = {
  name: appServicePlanName
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: appInsightsName
}

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing= {
  name: identityName
}


resource webApp 'Microsoft.Web/sites@2022-03-01' = {
  name: backendWebAppName
  location: location
    identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      
      linuxFxVersion: 'PYTHON|3.11'
      appCommandLine: 'gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app'      
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: '1'
        }        
        {
          name: 'AZURE_OPENAI_MODEL'
          value: 'gpt-4o'
        } 
        {
          name: 'AZURE_OPENAI_API_VERSION'
          value: '2025-01-01-preview'
        }      
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: OpenAIEndPoint
        } 
         {
          name: 'COSMOSDB_ENDPOINT'
          value: cosmosdbEnpoint
        } 
 {
          name: 'COSMOSDB_DATABASE'
          value: cosmosdbDatabase
        } 
         {
          name: 'COSMOSDB_HISTORY_CONTAINER'
          value: cosmosdbHistoryContainer
        } 
          {
          name: 'COSMOSDB_FEEDBACK_CONTAINER'
          value: cosmosdbFeedbackContainer
        } 
         {
          name: 'COSMOSDB_EVALUATIONS_CONTAINER'
          value: cosmosdbEvaluationContainer
        } 
        {
              name: 'AZURE_AI_SEARCH_ENDPOINT'
              value: searchServiceEndpoint
            } 
             {
              name: 'AZURE_AI_SEARCH_INDEX'
              value: 'policy-index'
            } 
            {
              name: 'AZURE_SEARCH_VECTOR_FIELD'
              value: 'content_vector'
            } 

        {
          name: 'AZURE_CLIENT_ID'
          value: managedIdentity.properties.clientId
        } 
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'ApplicationInsightsAgent_EXTENSION_VERSION'
          value: '~3'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }    

      ]
      alwaysOn: true
    }
    publicNetworkAccess: 'Enabled'
    
  }
 
}


resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2021-06-01'  existing =  {
  name: logAnalyticsWorkspaceName
}

resource diagnosticSettingsAPI 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: '${backendWebAppName}-diagnostic'
  scope: webApp
  properties: {
    workspaceId: logAnalyticsWorkspace.id
    logs: [
      {
        category: 'AppServiceHTTPLogs'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'AppServiceConsoleLogs'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'AppServiceAppLogs'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
  }
}


output backendWebAppURL string = 'https://${backendWebAppName}.azurewebsites.net'
output backendWebAppName string = backendWebAppName
