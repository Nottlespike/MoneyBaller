from uagents.setup import fund_agent_if_low
from uagents import Agent, Context, Protocol
 
agent = Agent(
    name="MoneyBaller",
    port=8000,
    seed="8a421c45b71382ac52709e55877541267c962c3236e84b858703567cc69f7e78",
    endpoint=["http://127.0.0.1:8000/submit"],
)
 
fund_agent_if_low(agent.wallet.address())
 
agent.run()