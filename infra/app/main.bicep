targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name representing the deployment environment (e.g., "dev", "test", "prod", "lab"); used to generate a short, unique hash for each resource')
param environmentName string

@minLength(1)
@maxLength(64)
@description('Name used to identify the project; also used to generate a short, unique hash for each resource')
param projectName string

@minLength(1)
@description('Azure region where all resources will be deployed (e.g., "eastus")')
param location string

@description('Name of the resource group where resources will be deployed')
param resourceGroupName string

@description('Token or string used to uniquely identify this resource deployment (e.g., build ID, commit hash)')
param resourceToken string

@description('Name of the User Assigned Managed Identity to assign to deployed services')
param managedIdentityName string

@description('Name of the Log Analytics Workspace for centralized monitoring')
param logAnalyticsWorkspaceName string

@description('Name of the Application Insights instance for telemetry')
param appInsightsName string

@description('Name of the App Service Plan for hosting web apps or APIs')
param appServicePlanName string

@description('Name of the Azure Key Vault used to store secrets and keys securely')
param keyVaultUri string

@description('Name of the Cosmos DB Endpoint')
param cosmosdbEnpoint string

@description('Endpoint URL of the Azure OpenAI resource (e.g., https://your-resource.openai.azure.com/)')
param OpenAIEndPoint string

@description('Name of the Azure AI Search service instance')
param searchServicename string

@description('Name of the Azure Storage Account used for blob or file storage')
param storageAccountName string


resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' existing =  {
  name: resourceGroupName
}



module appSecrets 'app-secrets.bicep' = {
  name: 'appSecrets'
  scope: resourceGroup
  params: {
    keyVaultName: keyVaultUri
    searchServicename: searchServicename
  }
}

module loaderFunctionWebApp 'loader-function-web-app.bicep' = {
  name: 'loaderFunctionWebApp'
  scope: resourceGroup
  params: { 
    location: location
    identityName: managedIdentityName
    functionAppName: 'func-loader-${resourceToken}'
    functionAppPlanName: appServicePlanName
    StorageAccountName: storageAccountName
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    appInsightsName: appInsightsName
    keyVaultUri:appSecrets.outputs.keyVaultUri
    OpenAIEndPoint: OpenAIEndPoint
    searchServiceEndpoint: appSecrets.outputs.searchServiceEndpoint
    azureAISearchKey: appSecrets.outputs.AzureAISearchKey
    azureAiSearchBatchSize: 100
    documentChunkOverlap: 500
    documentChunkSize: 2000
  
  }
}

module backEndWebApp 'backend-web-app.bicep' = { 
  name: 'backEndWebApp'
  scope: resourceGroup
   params: { 
    backendWebAppName: 'api-${projectName}-${environmentName}-${resourceToken}'
    appServicePlanName:appServicePlanName
    location: location
    identityName: managedIdentityName
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    appInsightsName: appInsightsName
    OpenAIEndPoint: OpenAIEndPoint
    cosmosdbEnpoint:cosmosdbEnpoint
    cosmosdbDatabase:'chatdatabase'
    cosmosdbHistoryContainer:'chathistory'
    cosmosdbEvaluationContainer:'evaluation'
   }
}


module frontEndWebApp 'frontend-web-app.bicep' = { 
  name: 'frontEndWebApp'
  scope: resourceGroup
   params: { 
    backendWebAppURL: backEndWebApp.outputs.backendWebAppURL
    frontendWebAppName: 'web-${projectName}-${environmentName}-${resourceToken}'
    appServicePlanName:appServicePlanName
    location: location
    identityName: managedIdentityName
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    appInsightsName: appInsightsName
   }
}

output functionAppName string =  loaderFunctionWebApp.outputs.functionAppName
output backEndWebAppName string =  backEndWebApp.outputs.backendWebAppName
output frontendWebAppName string = frontEndWebApp.outputs.frontendWebAppName
output appServiceURL string = frontEndWebApp.outputs.appServiceURL

