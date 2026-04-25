// argus — minimal mock data retained for out-of-scope screens that haven't
// been wired to live APIs yet (DebateRoom, ReplayScreen, OpsTheater,
// PersonaDesigner, CommandPalette). The in-scope screens (Home/KG/Library/
// Compare/World/Synthesis/Obs/Settings/Sources) no longer import any data
// from this file — they render real data or empty states.

export type Persona = {
  id: string;
  name: string;
  role: string;
  country: string;
  flag: string;
  color: string;
  colorVar: string;
  initials: string;
  bias: string;
  beliefs: string[];
  redlines: string[];
  model: string;
  memorySize: string;
  temperature: number;
  aggression: number;
  citationStrictness: number;
};

export type Cite = { n: number; src: string; label: string };

export type TranscriptMsg = {
  round: "DRAFT" | "CRITIQUE" | "REBUT" | "VOTE";
  roundN: number;
  persona: string;
  t: string;
  text: string;
  cites: Cite[];
  confidence: number;
  challenge?: string;
  references?: string[];
};

export type KGEntity = {
  id: string;
  label: string;
  type: string;
  x: number;
  y: number;
  deg: number;
};

export type OrchestrationNode = {
  id: string;
  label: string;
  x: number;
  y: number;
  model: string;
  state: "idle" | "thinking" | "tool-call" | "speaking" | "running";
  inEdges: string[];
  outEdges: string[];
};

export type RecentDebate = {
  id: string;
  title: string;
  time: string;
  personas: number;
  status: "running" | "done";
};

export const PERSONAS: Persona[] = [
  {
    id: "lai",
    name: "Lai Ching-te",
    role: "President of Taiwan (ROC)",
    country: "TW",
    flag: "🇹🇼",
    color: "p2",
    colorVar: "var(--p-2)",
    initials: "LC",
    bias: "Sovereignty-first, US-aligned",
    beliefs: ["Status quo preservation", "Democratic legitimacy", "Asymmetric defense"],
    redlines: [
      "No unilateral declaration of independence",
      "Will not accept 1992 Consensus framing",
    ],
    model: "claude-sonnet-4.5",
    memorySize: "12.4MB",
    temperature: 0.4,
    aggression: 0.55,
    citationStrictness: 0.85,
  },
  {
    id: "xi",
    name: "Xi Jinping",
    role: "General Secretary, CPC",
    country: "CN",
    flag: "🇨🇳",
    color: "p1",
    colorVar: "var(--p-1)",
    initials: "XJ",
    bias: "Reunification doctrine, anti-hegemony",
    beliefs: [
      "One China principle",
      "Peaceful reunification preferred, force not renounced",
      "Century of humiliation framing",
    ],
    redlines: ["Taiwan independence", "Foreign military stationed on Taiwan"],
    model: "claude-sonnet-4.5",
    memorySize: "18.1MB",
    temperature: 0.35,
    aggression: 0.78,
    citationStrictness: 0.7,
  },
  {
    id: "indopacom",
    name: "Adm. S. Paparo",
    role: "Cdr. US Indo-Pacific Command",
    country: "US",
    flag: "🇺🇸",
    color: "p3",
    colorVar: "var(--p-3)",
    initials: "SP",
    bias: "Deterrence-by-denial, alliance posture",
    beliefs: [
      "Hellscape strategy viable",
      "Munitions stockpile gap is critical",
      "Allies are force multipliers",
    ],
    redlines: ["Will not preemptively strike PLA mainland targets"],
    model: "claude-opus-4.1",
    memorySize: "9.8MB",
    temperature: 0.3,
    aggression: 0.62,
    citationStrictness: 0.92,
  },
  {
    id: "tsmc",
    name: "C.C. Wei",
    role: "CEO, TSMC",
    country: "TW",
    flag: "🇹🇼",
    color: "p4",
    colorVar: "var(--p-4)",
    initials: "CW",
    bias: "Operational continuity, supply-chain neutrality",
    beliefs: [
      "Silicon shield is real but bounded",
      "Arizona/Kumamoto fabs are insurance, not substitutes",
      "Two-year leadtime on EUV equipment",
    ],
    redlines: ["Will not relocate leading-edge node out of Taiwan absent existential risk"],
    model: "claude-sonnet-4.5",
    memorySize: "7.2MB",
    temperature: 0.45,
    aggression: 0.3,
    citationStrictness: 0.88,
  },
  {
    id: "ishiba",
    name: "Shigeru Ishiba",
    role: "Prime Minister, Japan",
    country: "JP",
    flag: "🇯🇵",
    color: "p5",
    colorVar: "var(--p-5)",
    initials: "SI",
    bias: "Counterstrike capability, Asian NATO advocate",
    beliefs: [
      "Taiwan emergency is Japan emergency",
      "Senkaku linkage",
      "Article 9 reinterpretation",
    ],
    redlines: ["Will not host offensive ground forces beyond Yonaguni"],
    model: "claude-sonnet-4.5",
    memorySize: "6.9MB",
    temperature: 0.42,
    aggression: 0.5,
    citationStrictness: 0.8,
  },
  {
    id: "analyst",
    name: "Bonny Lin",
    role: "Director, CSIS China Power",
    country: "US",
    flag: "🇺🇸",
    color: "p6",
    colorVar: "var(--p-6)",
    initials: "BL",
    bias: "Empirical, scenario-based",
    beliefs: [
      "Quarantine more likely than blockade",
      "Taiwan election cycle is escalation window",
      "Gray-zone is the war",
    ],
    redlines: [],
    model: "claude-opus-4.1",
    memorySize: "21.3MB",
    temperature: 0.55,
    aggression: 0.25,
    citationStrictness: 0.95,
  },
  {
    id: "citizen",
    name: "Composite: TW Citizen",
    role: "Aggregated public opinion (TW)",
    country: "TW",
    flag: "🇹🇼",
    color: "p7",
    colorVar: "var(--p-7)",
    initials: "公",
    bias: "Status-quo, prosperity-focused",
    beliefs: [
      "72% favor status quo",
      "Falling trust in US guarantees",
      "Conscription extension contested",
    ],
    redlines: [],
    model: "claude-haiku-4.5",
    memorySize: "3.1MB",
    temperature: 0.65,
    aggression: 0.2,
    citationStrictness: 0.6,
  },
];

export const TRANSCRIPT: TranscriptMsg[] = [
  {
    round: "DRAFT",
    roundN: 1,
    persona: "analyst",
    t: "00:00:04",
    text: "Framing the question. PLA Joint Sword 2026-A exercise concluded 78 hours ago with sustained PLAN presence inside the median line. The empirical question isn't *if* coercion escalates — it's whether the next rung is quarantine, blockade, or kinetic. I propose we anchor on quarantine — customs inspections, no kinetic — because it dominates recent doctrinal writing and lets Beijing test US response without Article-V-class escalation.",
    cites: [
      { n: 1, src: "GDELT", label: "PLA-EX-2026-04" },
      { n: 2, src: "CSIS", label: "China Maritime Studies #47" },
    ],
    confidence: 0.82,
  },
  {
    round: "DRAFT",
    roundN: 1,
    persona: "xi",
    t: "00:00:11",
    text: "The Party position is unchanged. Reunification is a historical inevitability, and the means are reserved to the Chinese people. What the analyst calls quarantine, we call lawful customs enforcement in our internal waters. The 2005 Anti-Secession Law authorizes non-peaceful means against secessionist activities — and the Lai administration's recent Indigenous Defense Submarine commissioning meets that threshold by our reading.",
    cites: [
      { n: 3, src: "Xinhua", label: "Anti-Secession Law Art.8" },
      { n: 4, src: "Reuters", label: "Hai Kun commissioning 2026-03-11" },
    ],
    confidence: 0.91,
  },
  {
    round: "DRAFT",
    roundN: 1,
    persona: "lai",
    t: "00:00:19",
    text: "Reject the premise. The Republic of China is a sovereign democracy of 23 million people. The 'internal waters' framing is a unilateral assertion contradicted by UNCLOS and by 75 years of practiced state-to-state relations. Our submarine program is defensive, transparent, and consistent with our obligations. Any quarantine is an act of war under customary international law, and we will treat it as such.",
    cites: [
      { n: 5, src: "UNCLOS", label: "Art.17 Innocent Passage" },
      { n: 6, src: "MOFA-TW", label: "Statement 2026-04-22" },
    ],
    confidence: 0.88,
  },
  {
    round: "DRAFT",
    roundN: 1,
    persona: "indopacom",
    t: "00:00:27",
    text: "INDOPACOM's planning assumption: a sustained quarantine forces a binary on Washington — break it or accept it. Breaking it requires escorting commercial traffic through claimed waters, which is a kinetic flashpoint. Accepting it concedes the precedent. Our preferred posture is *complicate the quarantine* — distributed maritime operations across the first island chain, and visible flow of munitions to Taiwan within 96 hours of trigger.",
    cites: [
      { n: 7, src: "DoD", label: "Indo-Pacific Strategy 2025" },
      { n: 8, src: "USNI", label: "Hellscape concept" },
    ],
    confidence: 0.79,
  },
  {
    round: "DRAFT",
    roundN: 1,
    persona: "tsmc",
    t: "00:00:34",
    text: "Operational reality: a 14-day port closure at Kaohsiung halts 38% of advanced-node wafer outflow. Arizona Fab 21 cannot absorb leading-edge demand — it runs N4P at ~20% of TW capacity. A 30-day event triggers force-majeure on every hyperscaler contract globally. We are not a war asset. We are a fragile node in a global system, and our customers will price that in within hours, not days.",
    cites: [{ n: 9, src: "TSMC IR", label: "Q1 2026 capacity disclosure" }],
    confidence: 0.94,
  },
  {
    round: "CRITIQUE",
    roundN: 2,
    persona: "analyst",
    t: "00:00:42",
    text: "Adm. Paparo — the 96-hour munitions flow assumes an open Bashi Channel. PLA Rocket Force has demonstrated capability to interdict. Is INDOPACOM's plan robust to a contested re-supply, or does it require uncontested access in the first 72 hours?",
    cites: [{ n: 10, src: "RAND", label: "PLARF 2024 capability assessment" }],
    confidence: 0.74,
    challenge: "indopacom",
  },
  {
    round: "CRITIQUE",
    roundN: 2,
    persona: "ishiba",
    t: "00:00:48",
    text: "Japan's position must be heard before this advances. A quarantine that closes the Bashi Channel forces traffic north through the Miyako Strait. That places PLA Navy assets within 110 nautical miles of Japanese sovereign territory — Yonaguni, Ishigaki. Under our 2022 reinterpretation, that is a *survival-threatening situation* triggering collective self-defense. Tokyo cannot be a spectator here. We will be a co-belligerent by geography alone.",
    cites: [
      { n: 11, src: "MOFA-JP", label: "NSS 2022" },
      { n: 12, src: "Diet", label: "Peace and Security Legislation 2015" },
    ],
    confidence: 0.86,
  },
  {
    round: "CRITIQUE",
    roundN: 2,
    persona: "citizen",
    t: "00:00:54",
    text: "The voices in this room speak for governments. Eight in ten of us want neither independence nor unification — we want the ferry to run, the chip plant to ship, our children to skip conscription. Every escalation rung described above is decided in capitals where we do not vote. The 'silicon shield' is a foreign policy concept; here it is the reason our cousins moved to Hsinchu and the reason our rents tripled. Please proceed knowing this.",
    cites: [{ n: 13, src: "ESC-TW", label: "April 2026 poll, n=1,247" }],
    confidence: 0.71,
  },
  {
    round: "REBUT",
    roundN: 3,
    persona: "indopacom",
    t: "00:01:03",
    text: "Conceded — the 96-hour figure assumes degraded but not denied access. Revised: under contested conditions, useful munitions delivery extends to 14–21 days for high-priority loadouts (ATACMS, NSM, Stinger), with submarine-delivered resupply as the residual channel. The plan is robust. The political question — whether the President orders it — is not mine to answer.",
    cites: [{ n: 14, src: "INDOPACOM", label: "TTX-Whirlwind 2025" }],
    confidence: 0.81,
    references: ["analyst"],
  },
  {
    round: "REBUT",
    roundN: 3,
    persona: "xi",
    t: "00:01:10",
    text: "The Japanese statement is noted and rejected. The 2022 reinterpretation is a domestic political document, not international law. Tokyo's intervention in a Chinese internal matter would be the most serious breach of the post-war order, and would invite responses calibrated to Japanese economic and territorial vulnerabilities — including but not limited to the Senkaku question, rare-earth flows, and the safety of the 110,000 PRC nationals resident in Japan.",
    cites: [{ n: 15, src: "Xinhua", label: "MoD statement 2026-04-19" }],
    confidence: 0.83,
    references: ["ishiba"],
  },
  {
    round: "REBUT",
    roundN: 3,
    persona: "lai",
    t: "00:01:17",
    text: "To the citizen voice — heard, and weighted. Our mandate is not to choose war, it is to make the cost of coercion higher than the benefit. Conscription extension was passed by the Legislative Yuan with 67% public support in March. The status quo the 80% wants is the status quo a credible deterrent produces. We will not trade legitimacy for calm.",
    cites: [{ n: 16, src: "LY-TW", label: "Bill 113-A vote record" }],
    confidence: 0.79,
    references: ["citizen"],
  },
  {
    round: "REBUT",
    roundN: 3,
    persona: "tsmc",
    t: "00:01:24",
    text: "One correction to the Adm.'s posture: visible munitions flow into Kaohsiung *during* a quarantine event will be read by markets as confirmation of impending kinetic action. The financial cascade — equity, FX, cross-border banking — will move faster than the military timeline. Plan for the markets to break before the missiles fly.",
    cites: [{ n: 17, src: "BIS", label: "TWD/USD stress test 2025" }],
    confidence: 0.87,
    references: ["indopacom"],
  },
  {
    round: "VOTE",
    roundN: 4,
    persona: "analyst",
    t: "00:01:32",
    text: "Synthesizing. Convergence on three points: (1) sustained quarantine is the modal next rung, probability 0.42 over 12mo, (2) Japan is structurally non-neutral, (3) the financial-shock vector precedes and may dominate the kinetic vector. Divergence remains on whether US escort posture is credible deterrent or tripwire. Recommending the synthesizer flag this as the open question.",
    cites: [],
    confidence: 0.88,
  },
];

export const KG_ENTITIES: KGEntity[] = [
  { id: "tw", label: "Republic of China (Taiwan)", type: "country", x: 0.5, y: 0.45, deg: 28 },
  { id: "cn", label: "People's Republic of China", type: "country", x: 0.32, y: 0.38, deg: 34 },
  { id: "us", label: "United States", type: "country", x: 0.78, y: 0.32, deg: 31 },
  { id: "jp", label: "Japan", type: "country", x: 0.62, y: 0.25, deg: 19 },
  { id: "lai", label: "Lai Ching-te", type: "person", x: 0.55, y: 0.55, deg: 12 },
  { id: "xi", label: "Xi Jinping", type: "person", x: 0.28, y: 0.48, deg: 17 },
  { id: "tsmc", label: "TSMC", type: "company", x: 0.48, y: 0.65, deg: 22 },
  { id: "pla", label: "PLA Eastern Theater", type: "org", x: 0.22, y: 0.58, deg: 14 },
  { id: "indopacom", label: "USINDOPACOM", type: "org", x: 0.85, y: 0.45, deg: 11 },
];

export const ORCHESTRATION: OrchestrationNode[] = [
  { id: "ingest", label: "INGEST", x: 0.08, y: 0.5, model: "—", state: "running", inEdges: [], outEdges: ["research"] },
  { id: "research", label: "RESEARCH", x: 0.24, y: 0.5, model: "haiku-4.5", state: "running", inEdges: ["ingest"], outEdges: ["kg", "orchestrator"] },
  { id: "kg", label: "KG WRITER", x: 0.24, y: 0.78, model: "haiku-4.5", state: "running", inEdges: ["research"], outEdges: [] },
  { id: "orchestrator", label: "ORCHESTRATOR", x: 0.45, y: 0.5, model: "opus-4.1", state: "thinking", inEdges: ["research"], outEdges: ["p-lai", "p-xi", "p-indo", "p-tsmc", "p-ishiba", "p-analyst", "p-citizen"] },
  { id: "p-lai", label: "LAI", x: 0.66, y: 0.18, model: "sonnet-4.5", state: "speaking", inEdges: ["orchestrator"], outEdges: ["synth"] },
  { id: "p-xi", label: "XI", x: 0.66, y: 0.30, model: "sonnet-4.5", state: "thinking", inEdges: ["orchestrator"], outEdges: ["synth"] },
  { id: "p-indo", label: "INDOPACOM", x: 0.66, y: 0.42, model: "opus-4.1", state: "tool-call", inEdges: ["orchestrator"], outEdges: ["synth"] },
  { id: "p-tsmc", label: "TSMC", x: 0.66, y: 0.54, model: "sonnet-4.5", state: "idle", inEdges: ["orchestrator"], outEdges: ["synth"] },
  { id: "p-ishiba", label: "ISHIBA", x: 0.66, y: 0.66, model: "sonnet-4.5", state: "idle", inEdges: ["orchestrator"], outEdges: ["synth"] },
  { id: "p-analyst", label: "ANALYST", x: 0.66, y: 0.78, model: "opus-4.1", state: "speaking", inEdges: ["orchestrator"], outEdges: ["synth"] },
  { id: "p-citizen", label: "CITIZEN", x: 0.66, y: 0.90, model: "haiku-4.5", state: "idle", inEdges: ["orchestrator"], outEdges: ["synth"] },
  { id: "synth", label: "SYNTHESIZER", x: 0.88, y: 0.5, model: "opus-4.1", state: "idle", inEdges: ["p-lai", "p-xi", "p-indo", "p-tsmc", "p-ishiba", "p-analyst", "p-citizen"], outEdges: [] },
];

export const RECENT: RecentDebate[] = [
  { id: "d-2026-04-25-01", title: "Taiwan Strait — quarantine vs blockade probability", time: "now", personas: 7, status: "running" },
  { id: "d-2026-04-24-04", title: "OPEC+ surprise cut: response stance", time: "18h", personas: 5, status: "done" },
  { id: "d-2026-04-24-02", title: "EU AI Act enforcement: first-mover liability", time: "1d", personas: 6, status: "done" },
  { id: "d-2026-04-23-07", title: "Fed pause vs cut at June FOMC", time: "1d", personas: 5, status: "done" },
];

export const ARGUS_DATA = {
  PERSONAS,
  TRANSCRIPT,
  KG_ENTITIES,
  ORCHESTRATION,
  RECENT,
};
