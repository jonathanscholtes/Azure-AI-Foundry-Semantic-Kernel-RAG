## Deployment: Azure AI Foundry and Dependencies

### **Prerequisites**
Ensure you have the following before deploying the solution:
- ✅ **Azure Subscription:** Active subscription with sufficient privileges to create and manage resources.  
- ✅ **Azure CLI:** Install the [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/get-started-with-azure-cli) for managing Azure resources.  
- ✅ **IDE with Bicep & PowerShell Support:** Use [VS Code](https://code.visualstudio.com/download) with the **Bicep extension** for development and validation.  

---

### **1. Clone the Repository**
Clone the project repository to your local machine:

```bash
git clone https://github.com/jonathanscholtes/Azure-AI-Foundry-Semantic-Kernel-RAG.git
cd Azure-AI-Foundry-Semantic-Kernel-RAG
```


### 2. Deploy the Solution  

Use the following PowerShell command to deploy the solution. Be sure to replace the placeholders with your actual subscription name and Azure region.


```powershell
.\deploy.ps1 -Subscription '[Your Subscription Name]' -Location 'eastus2' 
```

✅ This script provisions all required Azure resources based on the specified parameters. The deployment may take up to **40 minutes** to complete.



### 3.  Upload Documents for Indexing with Azure Function  

Upload the JSON documents from the [data](../data) directory to the **load** container in the Azure Storage Account. This upload will trigger the document processing function, which will chunk and index the documents into Azure AI Search. 


  