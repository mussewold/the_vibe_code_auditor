from src.state import AgentState

def prosecutor_node(state: AgentState) -> AgentState:
    """
    LangGraph node that performs the prosecutor's role:

    - Reviews the evidence and the opinions.
    - Provides a final report.
    """
    return {}


def defense_attorney_node(state: AgentState) -> AgentState: 
    """
    LangGraph node that performs the defense attorney's role:

    - Reviews the evidence and the opinions.
    - Provides a final report.
    """
    return {}


def tech_lead_node(state: AgentState) -> AgentState:
    """
    LangGraph node that performs the tech lead's role:  

    - Reviews the evidence and the opinions.
    - Provides a final report.
    """
    return {}