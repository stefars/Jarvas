from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from Agent.nodes import worker_node, tool_node, supervisor_node, worker_decide, route_worker, MessagesState



def make_agent():

    checkpointer = InMemorySaver()

    agent = StateGraph(MessagesState)

    agent.add_node("supervisor", supervisor_node)
    agent.add_node("worker", worker_node)
    agent.add_node("tools", tool_node)

    agent.add_conditional_edges(    #Router decides if the worker should be called or not.
        "supervisor",
        route_worker,
        {"worker": "worker", END: END}
    )

    agent.add_conditional_edges(  #If worker has tools, it goes to use them, or back to the supervisor.
        "worker",
        worker_decide,
        ["tools","supervisor","worker"]
    )
    agent.add_edge(START, "supervisor")
    agent.add_edge("tools", "worker")

    agent_compiled = agent.compile(checkpointer=checkpointer)
    return agent_compiled

class Jarvas:
    def __init__(self):
        self.agent = make_agent()

    def get_text(self,content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return str(content)

    def call(self, message : str) -> str:
        result = self.agent.invoke({"messages": [HumanMessage(content=message)]},
                             {"configurable": {"thread_id": "1"}})


        return self.get_text(result["messages"][-1].content)




def make_graph():
    try:
        graph_png = make_agent().get_graph(xray=True).draw_mermaid_png()

        with open("../agent_graph.png", "wb") as f:
            f.write(graph_png)

        print("Graph saved successfully as 'agent_graph.png'")
    except Exception as e:
        print(f"Could not generate graph: {e}")



#make_graph()

