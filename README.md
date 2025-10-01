> ⚠️  
> **This project is currently in active development and may contain breaking changes.**  
> Updates and modifications are being made frequently, which may impact stability or functionality. This notice will be removed once development is complete and the project reaches a stable release.  


# Azure AI Foundry + Semantic Kernel: Orchestrating Conversational Agents with Observability

## Overview  

This project demonstrates how **Azure AI Foundry Agent Service** and the **Semantic Kernel Agentic Framework** work together to deliver an end-to-end conversational knowledge agent system. The solution is enhanced with observability and monitoring provided by supporting agents.  

In this example, data is vectorized and loaded into **Azure Cosmos DB** using **Azure Durable Functions**. The primary conversational agent, built with the Semantic Kernel Agent Framework and **Azure AI Search**, retrieves knowledge documents while preserving chat history and evaluation metrics in Cosmos DB. Additional monitoring agents, deployed with Azure AI Foundry Agent Service and executed via Azure Durable Functions, provide performance analysis and compliance insights, offering feedback to improve accuracy, reliability, and overall effectiveness.  

---

## Key Features  

- **End-to-End Agentic System**  
  Orchestrates multiple agents using Azure AI Foundry Agent Service and Semantic Kernel.  

- **Conversational Knowledge Agent**  
  Implements Retrieval-Augmented Generation (RAG) with Azure AI Search.  
  Maintains chat history and evaluation metrics in Cosmos DB.  

- **Observability and Monitoring Agents**  
  Continuously evaluate performance, compliance, and conversational quality.  
  Deliver actionable insights for fine-tuning and continuous improvement.  

- **Durable Orchestration with Azure Durable Functions**  
  Automates vectorization and ingestion into Cosmos DB.  
  Coordinates agent workflows and long-running background processes.  

- **Conversational Agent Hosting**  
  Runs on **Azure App Service** with a **FastAPI backend** for scalable and secure API hosting.  

- **Modern Front-End Integration**  
  Provides a responsive user experience through a **ReactJS-based frontend** integrated with the FastAPI backend.  

- **Agent Memory Store**  
  Uses **Azure Cosmos DB** as the persistent memory layer, storing conversation history, embeddings, and evaluation metrics for both context-aware responses and monitoring.  

---

## 📐  Architecture

![design](/media/diagram2.png)

---


## 🛠️ **Core Steps for Solution Implementation**

Follow these key steps to successfully deploy and configure the solution:


### 1️⃣ [**Deploy the Solution**](docs/deployment.md)
- Detailed instructions for deploying solution, including prerequisites, configuration steps, and setup validation.   



## Repo layout (where to look)

- `infra/` — Bicep modules to provision core cloud resources (search, storage, functions, web, AI resources).
- `src/api/` — FastAPI-based agent host and example plugins (search, evaluation, history persistence).
- `src/DocumentProcessingFunction/` — Azure Function to chunk documents and push vectors into Azure AI Search.
- `src/EvaluationAnalyzerFunction/` — Functions for evaluation and analysis workflows.
- `src/Notebooks/` — Notebooks that demonstrate live agent interactions, evaluations, and analysis.
- `src/web/` — Optional React client used for demos and manual testing.
- `scripts/` — helpers for packaging and deployment artifacts.

---

## ♻️ **Clean-Up**

After completing the workshop and testing, ensure you delete any unused Azure resources or remove the entire Resource Group to avoid additional charges.

---

## 📜 License  
This project is licensed under the [MIT License](LICENSE.md), granting permission for commercial and non-commercial use with proper attribution.

---

## Disclaimer  
This workshop and demo application are intended for educational and demonstration purposes. It is provided "as-is" without any warranties, and users assume all responsibility for its use.