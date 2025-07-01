"""Main entrypoint for the conversational retrieval graph.

This module defines the core structure and functionality of the conversational
retrieval graph. It includes the main graph definition, state management,
and key functions for processing & routing user queries, generating research plans to answer user questions,
conducting research, and formulating responses.
"""

from typing import Any, Literal, TypedDict, cast

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage, FunctionMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from backend.retrieval_graph.configuration import AgentConfiguration
from backend.retrieval_graph.researcher_graph.graph import graph as researcher_graph
from backend.retrieval_graph.state import AgentState, InputState, Router
from backend.utils import format_docs, load_chat_model
from pydantic import BaseModel
from pydantic_ai import Agent


async def analyze_and_route_query(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, Router]:
    """Analyze the user's query and determine the appropriate routing.

    This function uses a language model to classify the user's query and decide how to route it
    within the conversation flow.

    Args:
        state (AgentState): The current state of the agent, including conversation history.
        config (RunnableConfig): Configuration with the model used for query analysis.

    Returns:
        dict[str, Router]: A dictionary containing the 'router' key with the classification result (classification type and logic).
    """
    # allow skipping the router for testing
    if state.router and state.router["logic"]:
        return {"router": state.router}

    configuration = AgentConfiguration.from_runnable_config(config)
    structured_output_kwargs = {}
    messages = []
    for m in state.messages:
        if hasattr(m, 'role') and hasattr(m, 'content'):
            messages.append({"role": m.role, "content": m.content})

    if "google_genai" in configuration.query_model:
        class RouterModel(BaseModel):
            logic: str
            type: Literal["more-info", "langchain", "general"]
        agent = Agent(
            configuration.query_model.replace("google_genai/", "google-gla:"),
            output_type=RouterModel,
            system_prompt=configuration.router_system_prompt,
        )
        # Fallback: Use only the last user message as a string for Gemini
        user_message = ""
        for m in reversed(state.messages):
            if isinstance(m, HumanMessage):
                user_message = m.content
                break
        response = await agent.run(user_message)
        return {"router": Router(logic=response.output.logic, type=response.output.type)}
    else:
        model = load_chat_model(configuration.query_model).with_structured_output(
            Router, **structured_output_kwargs
        )
        response = cast(Router, await model.ainvoke(messages))
        return {"router": response}


def route_query(
    state: AgentState,
) -> Literal["create_research_plan", "ask_for_more_info", "respond_to_general_query"]:
    """Determine the next step based on the query classification.

    Args:
        state (AgentState): The current state of the agent, including the router's classification.

    Returns:
        Literal["create_research_plan", "ask_for_more_info", "respond_to_general_query"]: The next step to take.

    Raises:
        ValueError: If an unknown router type is encountered.
    """
    _type = state.router["type"]
    if _type == "langchain":
        return "create_research_plan"
    elif _type == "more-info":
        return "ask_for_more_info"
    elif _type == "general":
        return "respond_to_general_query"
    else:
        raise ValueError(f"Unknown router type {_type}")


async def ask_for_more_info(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    """Generate a response asking the user for more information.

    This node is called when the router determines that more information is needed from the user.

    Args:
        state (AgentState): The current state of the agent, including conversation history and router logic.
        config (RunnableConfig): Configuration with the model used to respond.

    Returns:
        dict[str, list[str]]: A dictionary with a 'messages' key containing the generated response.
    """
    configuration = AgentConfiguration.from_runnable_config(config)
    model = load_chat_model(configuration.query_model)
    system_prompt = configuration.more_info_system_prompt.format(
        logic=state.router["logic"]
    )
    messages = [{"role": "system", "content": system_prompt}] + state.messages
    response = await model.ainvoke(messages)
    return {"messages": [response]}


async def respond_to_general_query(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    """Generate a response to a general query not related to LangChain.

    This node is called when the router classifies the query as a general question.

    Args:
        state (AgentState): The current state of the agent, including conversation history and router logic.
        config (RunnableConfig): Configuration with the model used to respond.

    Returns:
        dict[str, list[str]]: A dictionary with a 'messages' key containing the generated response.
    """
    configuration = AgentConfiguration.from_runnable_config(config)
    model = load_chat_model(configuration.query_model)
    system_prompt = configuration.general_system_prompt.format(
        logic=state.router["logic"]
    )
    messages = [{"role": "system", "content": system_prompt}] + state.messages
    response = await model.ainvoke(messages)
    return {"messages": [response]}


async def create_research_plan(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, list[str]]:
    """Create a step-by-step research plan for answering a LangChain-related query.

    Args:
        state (AgentState): The current state of the agent, including conversation history.
        config (RunnableConfig): Configuration with the model used to generate the plan.

    Returns:
        dict[str, list[str]]: A dictionary with a 'steps' key containing the list of research steps.
    """

    class PlanModel(BaseModel):
        steps: list[str]

    configuration = AgentConfiguration.from_runnable_config(config)
    structured_output_kwargs = {}
    messages = []
    for m in state.messages:
        if hasattr(m, 'role') and hasattr(m, 'content'):
            messages.append({"role": m.role, "content": m.content})

    if "google_genai" in configuration.query_model:
        agent = Agent(
            configuration.query_model.replace("google_genai/", "google-gla:"),
            output_type=PlanModel,
            system_prompt=configuration.research_plan_system_prompt,
        )
        # Fallback: Use only the last user message as a string for Gemini
        user_message = ""
        for m in reversed(state.messages):
            if isinstance(m, HumanMessage):
                user_message = m.content
                break
        response = await agent.run(user_message)
        return {"steps": response.output.steps}
    else:
        model = load_chat_model(configuration.query_model).with_structured_output(
            PlanModel, **structured_output_kwargs
        )
        response = cast(PlanModel, await model.ainvoke(messages))
        return {"steps": response.steps}


async def conduct_research(state: AgentState) -> dict[str, Any]:
    """Execute the first step of the research plan.

    This function takes the first step from the research plan and uses it to conduct research.

    Args:
        state (AgentState): The current state of the agent, including the research plan steps.

    Returns:
        dict[str, list[str]]: A dictionary with 'documents' containing the research results and
                              'steps' containing the remaining research steps.

    Behavior:
        - Invokes the researcher_graph with the first step of the research plan.
        - Updates the state with the retrieved documents and removes the completed step.
    """
    result = await researcher_graph.ainvoke({"question": state.steps[0]})
    return {"documents": result["documents"], "steps": state.steps[1:]}


def check_finished(state: AgentState) -> Literal["respond", "conduct_research"]:
    """Determine if the research process is complete or if more research is needed.

    This function checks if there are any remaining steps in the research plan:
        - If there are, route back to the `conduct_research` node
        - Otherwise, route to the `respond` node

    Args:
        state (AgentState): The current state of the agent, including the remaining research steps.

    Returns:
        Literal["respond", "conduct_research"]: The next step to take based on whether research is complete.
    """
    if len(state.steps or []) > 0:
        return "conduct_research"
    else:
        return "respond"


async def respond(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    """Generate a final response to the user's query based on the conducted research.

    This function formulates a comprehensive answer using the conversation history and the documents retrieved by the researcher.

    Args:
        state (AgentState): The current state of the agent, including conversation history, router logic, and retrieved documents.
        config (RunnableConfig): Configuration with the model used to generate the response.

    Returns:
        dict[str, list[BaseMessage]]: A dictionary with a 'messages' key containing the generated response.

    Behavior:
        - Formats the retrieved documents for context.
        - Constructs a system prompt that includes the router's logic and the formatted documents.
        - Generates a comprehensive response using the language model.
    """
    configuration = AgentConfiguration.from_runnable_config(config)
    model = load_chat_model(configuration.response_model)
    system_prompt = configuration.response_system_prompt.format(
        logic=state.router["logic"], docs=format_docs(state.documents)
    )
    messages = [{"role": "system", "content": system_prompt}] + state.messages
    response = await model.ainvoke(messages)
    return {"messages": [response]}


# Define the graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("analyze_and_route_query", analyze_and_route_query)
builder.add_node("ask_for_more_info", ask_for_more_info)
builder.add_node("respond_to_general_query", respond_to_general_query)
builder.add_node("create_research_plan", create_research_plan)
builder.add_node("conduct_research", conduct_research)
builder.add_node("respond", respond)

# Add edges
builder.add_edge(START, "analyze_and_route_query")
builder.add_conditional_edges(
    "analyze_and_route_query",
    route_query,
    {
        "ask_for_more_info": "ask_for_more_info",
        "respond_to_general_query": "respond_to_general_query",
        "create_research_plan": "create_research_plan",
    },
)
builder.add_edge("ask_for_more_info", END)
builder.add_edge("respond_to_general_query", END)
builder.add_edge("create_research_plan", "conduct_research")
builder.add_conditional_edges(
    "conduct_research",
    check_finished,
    {
        "conduct_research": "conduct_research",
        "respond": "respond",
    },
)
builder.add_edge("respond", END)

# Compile into a graph object that you can invoke and deploy.
graph = builder.compile()
graph.name = "ConversationalRetrievalGraph"
