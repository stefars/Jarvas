from typing import TypedDict, Annotated, Literal
import operator
from langgraph.graph import END
from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field
from Utils.tools import TOOLS
from Agent.models import gemini_model, worker_gemini_model
from logging import info, debug
from Agent.prompts import *




tools_by_name = {tool.name: tool for tool in TOOLS}

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    message_type: str | None
    request: str | None
    next_step: Literal["worker",END]
    status: Literal["complete","incomplete","request"]
class MessageClassifier(BaseModel):
    message_type: Literal["perform_action", "informational"] = Field(
        ...,
        description="Classify if the message require an action to be performed (perform_action) or "
                    "is asking information that are not related to files on the system."
    )
    request: str = Field(
        ...,
        description="""Tell the worker what to do. Include keywords, arguments, details, and any details
                        you can infer from the user message."""
    )
class ResultValidation(BaseModel):
    status: Literal["complete","incomplete","request"]
    notes: str = Field(
        ...,
        description="""If status is complete, pass the information to the user, if it's incomplete, explain 
        what should be done to achieve the goal. If you have a request, specify it."""
    )




def get_safe_context(messages, limit=5):
    # Take the last 'limit' messages
    slice_window = messages[-limit:]

    # If the first message in our slice is a ToolMessage,
    # it's 'orphaned'. We should include the message before it too.
    if slice_window and isinstance(slice_window[0], ToolMessage):
        # Extend the slice back by one more to catch the AIMessage trigger
        slice_window = messages[-(limit + 1):]

    return slice_window

# SUPERVISOR
def supervisor_node(state: MessagesState) -> dict:


    # Check if response came from the Worker:
    last_message = state["messages"][-1]

    info(f"last_message type: {type(last_message)}")
    info(f"last_message: {last_message}")


    # if the task is complete, display the worker response.
    if state.get("status") in ["complete","blocked"]:
        info("Ending task...")
        return {"next_step": END,"status":"incomplete"}



    classifier_llm = gemini_model.with_structured_output(MessageClassifier)






    classified = classifier_llm.invoke([CLASSIFIER_INSTRUCTION, last_message])
    info(classified.message_type)

    if classified.message_type == "informational":


        result = gemini_model.invoke([SUPERVISOR_INSTRUCTION] + state["messages"])
        info(result)


        #if worker by any chance answers a question, supervisor will just get back to worker.
        next_step = "worker" if state.get("status") == "request" else END

        return {
            "request": classified.request,
            "messages": [result],
            "next_step": next_step
        }


    if classified.message_type == "perform_action":
        return {
            "request": classified.request,
            "next_step": "worker",
            "status": "incomplete"
        }




    # If informational, the supervisor has access to request info, and finds it.
    # If perform_action, the supervisor will make a brief description of the action required.

    return {"next_step": END}




def worker_decide(state: MessagesState) -> Literal["tools", "supervisor","worker"]:
    # after the worker reasons and inputs his actions
    # we verify if there are any tools to use (and maybe other validations)

    last_msg = state["messages"][-1]



    status = state.get("status")
    info(f"worker_decide status: {status}")
    if status in ["complete","request","blocked"]:
        return "supervisor"

        # if has tool calls go to tools, if it has no tool calls (and is incomplete) go to worker
    val = "tools" if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls else "worker"

    info(f"worker_decide decision: {val}")


    return val


def worker_node(state: MessagesState) -> dict:
    """Worker with tools."""
    latest_human = next((m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None)
    last_msg = state["messages"][-1]
    request = state.get("request")


    info(f"received in worker_node: {last_msg}")
    info(f"last human message: {latest_human}")
    info(f"request recieved in worker_node {request}")


    # First ve  eval_messages = [rify if last message is from tools.
    if isinstance(last_msg, ToolMessage):
        info("message is a tool_call")
        # Worker analyzes and decides if the request is sufficient.
        tool_id = last_msg.tool_call_id
        ai_trigger_msg = next(
            (m for m in reversed(state["messages"])
             if isinstance(m, AIMessage) and
             any(tc['id'] == tool_id for tc in getattr(m, 'tool_calls', []))),
            None
        )



        eval_messages = [
            AUDITOR_INSTRUCTION,
            latest_human,
            ai_trigger_msg,
            last_msg
        ]

        info(eval_messages)


        debug(f"Several info: tool: {last_msg.content}, human: {latest_human}")

        evaluate = gemini_model.with_structured_output(ResultValidation)
        eval_result = evaluate.invoke(eval_messages)

        info(f"eval_results in worker_node: {eval_result}")

        if eval_result.status in ["complete", "request", "blocked"]:
            return {"messages": [HumanMessage(content=f"{eval_result.notes}")], "status": eval_result.status}

        if eval_result.status == "incomplete":
            print(f"[WORKER THINKING]: {eval_result.notes}")
            feedback = HumanMessage(
                content=f"Attempt failed. Evaluator notes: {eval_result.notes}. Please try something else.")
            return {"messages": [feedback], "status": "incomplete"}

    else:
        info("message is a human_message")




    formatted_text = WORKER_INSTRUCTION.format(request=request)
    system_msg = SystemMessage(content=formatted_text)


    # Takes the request context and executes the request.
    response = worker_gemini_model.bind_tools(TOOLS).invoke([system_msg] + state["messages"])

    info(f"response={response}")
    info(f"content= {response.content}")
    info(f"tool_calls= {response.tool_calls}")


    #if no tool calls, it could either be: "request" as it needs info from supervisor, or "complete" as there is nothing new it can add.
    #request is gonna feed back into worker.
    if len(response.tool_calls) == 0:
        if "REQUEST" in response.content:
            return {"messages": [HumanMessage(response.content)], "status":"request"} #prolematic line, it will always be request if there is no tool call.
        return {"messages": [HumanMessage(response.content)], "status": "complete"}

    return {"messages": [response]}


def tool_node(state: MessagesState) -> dict:
    """Execute tools."""
    last_msg = state["messages"][-1]

    debug(f"current tool_call: {last_msg.tool_calls}")
    results = []

    for tc in getattr(last_msg, 'tool_calls', []):
        name = tc['name']
        if name not in tools_by_name:
            # Tell the model it made a mistake so it can correct itself
            obs = f"Error: Tool '{name}' does not exist. Please use only allowed tools or iterpret yourself."
        else:
            tool = tools_by_name[name]
            try:
                obs = tool.invoke(tc['args'])
            except Exception as e:
                obs = f"Error executing {name}: {e}"
        results.append(ToolMessage(content=str(obs), tool_call_id=tc['id']))

    debug(f"tool call results {results}")
    return {"messages": results}







def route_worker(state: MessagesState) -> Literal["worker", END]:
    next_step = state.get("next_step")

    info(f"route_worker decision: {next_step}")

    return next_step if next_step == "worker" else END