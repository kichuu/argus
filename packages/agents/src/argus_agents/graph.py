from typing import Any
from uuid import UUID, uuid4

from argus_core.logging import get_logger
from argus_extraction.providers import Provider, family_of
from langgraph.graph import END, StateGraph

from argus_agents.critic import CriticAgent
from argus_agents.master import MasterAgent
from argus_agents.persona import PersonaAgent
from argus_agents.research import ResearchAgent
from argus_agents.state import DiscussionState, EvidencePack
from argus_agents.synthesizer import SynthesizerAgent

logger = get_logger(__name__)


class DiscussionGraph:
    def __init__(
        self,
        retriever: Any,
        master_provider: Provider,
        persona_provider: Provider,
        critic_provider: Provider,
        synth_provider: Provider,
        *,
        research_model: str,
        master_model: str,
        persona_model: str,
        critic_model: str,
        synth_model: str,
        extractor_family: str,
    ) -> None:
        self.research = ResearchAgent(retriever, research_model)
        self.master = MasterAgent(master_provider, master_model)
        self.persona_provider = persona_provider
        self.persona_model = persona_model
        self.critic = CriticAgent(critic_provider, critic_model, extractor_family)
        self.synth = SynthesizerAgent(synth_provider, synth_model)
        self.extractor_family = extractor_family
        self._compiled = self._build()

    def _build(self) -> Any:
        builder: StateGraph = StateGraph(DiscussionState)

        async def research_node(state: DiscussionState) -> DiscussionState:
            return await self.research.step(state)

        async def master_node(state: DiscussionState) -> DiscussionState:
            return await self.master.step(state)

        # TODO: parallel fan-out across personas via LangGraph Send API
        # once we adopt 0.3.x. For 0.2.x, sequential execution keeps state
        # merge semantics simple.
        async def personas_node(state: DiscussionState) -> DiscussionState:
            for persona in state.personas:
                agent = PersonaAgent(persona, self.persona_provider, self.persona_model)
                state = await agent.step(state)
            return state

        async def critic_node(state: DiscussionState) -> DiscussionState:
            # sanity-check at runtime: critic must not share extractor family
            if family_of(self.persona_model).lower() == self.extractor_family.lower():
                logger.warning(
                    "persona_extractor_same_family",
                    persona_family=family_of(self.persona_model),
                    extractor_family=self.extractor_family,
                )
            return await self.critic.step(state)

        async def synth_node(state: DiscussionState) -> DiscussionState:
            return await self.synth.step(state)

        builder.add_node("research", research_node)
        builder.add_node("master", master_node)
        builder.add_node("personas", personas_node)
        builder.add_node("critic", critic_node)
        builder.add_node("synthesizer", synth_node)

        builder.set_entry_point("research")
        builder.add_edge("research", "master")
        builder.add_edge("master", "personas")
        builder.add_edge("personas", "critic")
        builder.add_edge("critic", "synthesizer")
        builder.add_edge("synthesizer", END)

        return builder.compile()

    async def run(
        self,
        topic: str,
        *,
        discussion_id: UUID | None = None,
    ) -> DiscussionState:
        initial = DiscussionState(
            discussion_id=discussion_id or uuid4(),
            topic=topic,
            evidence_pack=EvidencePack(topic=topic),
        )
        result = await self._compiled.ainvoke(initial)
        if isinstance(result, DiscussionState):
            return result
        # LangGraph may return a dict in some versions
        return DiscussionState.model_validate(result)
