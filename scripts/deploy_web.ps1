param (
    [string]$webAppName,
    [string]$resourceGroupName,
    [string]$apiURL,
    [string]$appPath
)

#$nodeAppPath = "..\..\src\web"
$nodeTempDir = "artifacts\web\temp"
$nodeBuildDir = "${appPath}\build"
$zipFilePath = "artifacts\web\app.zip"


Set-Content -Path "$appPath\.env" -Value "REACT_APP_API_HOST=$apiURL"

Start-Process "npm" -ArgumentList "install" -WorkingDirectory $appPath -NoNewWindow -Wait

Start-Process "npm" -ArgumentList "run build" -WorkingDirectory $appPath -NoNewWindow -Wait


# Construct the argument list
$args = "$nodeBuildDir $zipFilePath $nodeTempDir  --exclude_files .env .gitignore *.md"

# Execute the Python script
Start-Process "python" -ArgumentList "directory_zipper.py $args" -NoNewWindow -Wait

# Deploy the zip file to the Azure Web App
az webapp deploy --resource-group $resourceGroupName --name $webAppName --src-path $zipFilePath --type 'zip' --timeout 60000

# Clean up zip file
#Remove-Item $zipFilePath