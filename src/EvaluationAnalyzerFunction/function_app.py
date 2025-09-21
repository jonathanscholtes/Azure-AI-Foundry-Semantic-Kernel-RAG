import azure.functions as func
import azure.durable_functions as df
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.cosmos.aio import CosmosClient
import logging
import traceback
from os import environ
from datetime import datetime
import json
import uuid
from typing import List

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@myApp.route(route="orchestrators/{functionName}")
@myApp.durable_client_input(client_name="client")
async def start_evaluations(req: func.HttpRequest, client):

    function_name = req.route_params.get('functionName')

    # Try to get JSON body
    try:
        params = req.get_json()
    except ValueError:
        # Fallback: get from query string
        params = {
            "agent": req.params.get("agent"),
            "date": req.params.get("date")
        }

    # Validate required parameters
    if not params.get("agent") or not params.get("date"):
        return func.HttpResponse(
            "Missing required parameters 'agent' and 'date'.",
            status_code=400
        )
    
    #{"agent": "HR_Agent", "date": "2025-09-21"}
    
    instance_id = await client.start_new(function_name, None,params )
    
    response = client.create_check_status_response(req, instance_id)
    return response


@myApp.orchestration_trigger(context_name="context")
def eval_orchestrator(context: df.DurableOrchestrationContext):
    """
    Orchestrates querying Cosmos DB, processing evaluations, batching, 
    calling agent activities, and summarizing results.
    """
    params = context.get_input()  # e.g., {"agent": "HR_Agent", "date": "2025-09-21"}

    # Step 1: query Cosmos DB
    records = yield context.call_activity("query_cosmos_activity", params)

    if not records:
        # Return early if no records found
        logging.info(f"No records found for agent={params['agent']} on date={params['date']}")
        return {"status": "no_records", "data": []}

    # Step 2: flatten records (remove 'pass' evaluators)
    flattened = yield context.call_activity("flatten_activity", records)

    if not flattened:
        return {"status": "no_failed_records", "data": []}

    # Step 3: batch flattened records
    batch_size = 20  ## Create ENV Var
    batches = [flattened[i:i+batch_size] for i in range(0, len(flattened), batch_size)]

    # Step 4: fan-out batch analysis agent calls
    tasks = [context.call_activity("batch_analysis_agent_activity", b) for b in batches]
    batch_summaries = yield context.task_all(tasks)

    # Step 5: call final summarizer agent
    final_summary = yield context.call_activity("final_summarizer_agent_activity", batch_summaries)

    # Step 6: optionally save final summary to Cosmos
    save_payload = {
        "instance_id": context.instance_id,
        "agent": params.get("agent"),
        "date": params.get("date"),
        "final_summary": final_summary.get("final_summary"),
        "batch_summaries": batch_summaries
    }
    yield context.call_activity("save_summary_to_cosmos", save_payload)

    return final_summary


@myApp.activity_trigger(input_name="params")
async def query_cosmos_activity(params: dict) -> List[dict]:
    url = environ["COSMOSDB_ENDPOINT"]
    database_name = environ["COSMOSDB_DATABASE"]
    container_name = environ["COSMOSDB_EVALUATIONS_CONTAINER"]

    if not url or not database_name:
        missing = [
            name
            for name, value in [
                ("COSMOSDB_ENDPOINT", url),
                ("COSMOSDB_DATABASE", database_name),
                ("COSMOSDB_EVALUATIONS_CONTAINER", container_name),
            ]
            if not value
        ]
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    credential = DefaultAzureCredential()
    client = CosmosClient(url, credential=credential)
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)

    query = f"""
    SELECT c.id, c.sessionid, c.user_query, c.response, c.evaluation, c.metadata.agent, c.timestamp
    FROM c
    WHERE c.metadata.agent = "{params['agent']}"
      AND STARTSWITH(c.timestamp, "{params['date']}")
      AND (
            c.evaluation.groundedness.groundedness_result = "fail"
         OR c.evaluation.coherence.coherence_result = "fail"
         OR c.evaluation.relevance.relevance_result = "fail"
      )
    """

    results = []
    async for item in container.query_items(query=query):
        results.append(item)

    await client.close()  # Close async client
    return results


@myApp.activity_trigger(input_name="records")
def flatten_activity(records: List[dict]) -> List[dict]:
    flattened = []

    if not records:
        logging.info("No records provided to flatten_activity.")
        return flattened

    for item in records:
        evals = item.get("evaluation", {})
        failed = {k: v for k, v in evals.items() if v.get(f"{k}_result") == "fail"}

        flattened.append({
            "id": item.get("id"),
            "sessionid": item.get("sessionid"),
            "user_query": item.get("user_query"),
            "response": item.get("response"),
            "agent": item.get("metadata", {}).get("agent"),
            "timestamp": item.get("timestamp"),
            "failed_evaluations": failed
        })

    logging.info(f"Flattened {len(flattened)} records with failed evaluations.")
    return flattened



@myApp.activity_trigger(input_name="batch")
def batch_analysis_agent_activity(batch: List[dict]) -> dict:
    """
    Summarize a batch of evaluation failures using Azure AI Foundry agent.
    """
    # Flatten batch into a single text input
    text = "\n".join([
        f"Q: {r['user_query']} | Failures: {list(r['failed_evaluations'].keys())}"
        for r in batch
    ])

    # Initialize Foundry client
    project_client = AIProjectClient(
        endpoint=environ["PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential()
    )
    agent_id = environ["BATCH_ANALYZER_AGENT_ID"]

    # Create a thread for this batch
    thread = project_client.agents.threads.create()
    thread_id = thread.id

    # Send user message
    project_client.agents.messages.create(
        thread_id=thread_id,
        role="user",
        content=text
    )

    # Create and process the run
    run = project_client.agents.runs.create_and_process(
        thread_id=thread_id,
        agent_id=agent_id
    )

    if run.status == "failed":
        return {"batch_summary": "Error: failed to process batch."}

    # Fetch the latest assistant message
    messages = project_client.agents.messages.list(thread_id=thread_id)
    for msg in messages:
        if msg.role == "assistant":
            content = ""
            for c in msg.content:
                if hasattr(c, "text") and hasattr(c.text, "value"):
                    content += c.text.value
                elif hasattr(c, "value"):
                    content += str(c.value)
            return {"batch_summary": content}

    return {"batch_summary": "No response generated."}



@myApp.activity_trigger(input_name="batch_summaries")
def final_summarizer_agent_activity(batch_summaries: List[dict]) -> dict:
    """
    Consolidate multiple batch summaries into a final summary using Azure AI Foundry agent.
    """
    # Join all batch summaries into a single prompt
    text = "\n".join([s["batch_summary"] for s in batch_summaries])

    # Initialize Foundry client
    project_client = AIProjectClient(
        endpoint=environ["PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential()
    )
    agent_id = environ["FINAL_SUMMARIZER_AGENT_ID"]

    # Create a thread for the summarization
    thread = project_client.agents.threads.create()
    thread_id = thread.id

    # Send user message
    project_client.agents.messages.create(
        thread_id=thread_id,
        role="user",
        content=text
    )

    # Create and process the run
    run = project_client.agents.runs.create_and_process(
        thread_id=thread_id,
        agent_id=agent_id
    )

    if run.status == "failed":
        return {"final_summary": "Error: failed to generate final summary."}

    # Fetch the latest assistant message
    messages = project_client.agents.messages.list(thread_id=thread_id)
    for msg in messages:
        if msg.role == "assistant":
            content = ""
            for c in msg.content:
                if hasattr(c, "text") and hasattr(c.text, "value"):
                    content += c.text.value
                elif hasattr(c, "value"):
                    content += str(c.value)
            return {"final_summary": content, "batch_summaries": batch_summaries}

    return {"final_summary": "No response generated.", "batch_summaries": batch_summaries}


@myApp.activity_trigger(input_name="summary_data")
async def save_summary_to_cosmos(summary_data: dict) -> dict:
    url = environ["COSMOSDB_ENDPOINT"]
    database_name = environ["COSMOSDB_DATABASE"]
    container_name = environ["COSMOSDB_SUMMARY_CONTAINER"]

    if not url or not database_name:
        missing = [
            name
            for name, value in [
                ("COSMOSDB_ENDPOINT", url),
                ("COSMOSDB_DATABASE", database_name),
                ("COSMOSDB_SUMMARY_CONTAINER", container_name),
            ]
            if not value
        ]
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    credential = DefaultAzureCredential()
    client = CosmosClient(url, credential=credential)
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)



    doc = {
        "id": summary_data.get("instance_id"),  # use orchestration instance ID
        "agent": summary_data.get("agent"),
        "date": summary_data.get("date"),
        "final_summary": summary_data.get("final_summary"),
        "batch_summaries": summary_data.get("batch_summaries"),
        "timestamp": datetime.utcnow().isoformat()
    }

    await container.create_item(doc)
    return {"status": "saved", "id": doc["id"]}