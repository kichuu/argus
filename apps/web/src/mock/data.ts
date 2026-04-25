// argus — mock data ported from design/argus/project/data.js with TS types

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

export type Source = {
  id: string;
  name: string;
  type: string;
  status: "ok" | "warn" | "down";
  latency: number;
  errorRate: number;
  lastUpdate: string;
  coverage: string;
  quality: number;
};

export type GeoEvent = {
  id: string;
  lat: number;
  lon: number;
  label: string;
  topic: string;
  severity: number;
  country: string;
};

export type Hotspot = {
  rank: number;
  label: string;
  topic: string;
  events24h: number;
  delta: string;
  severity: number;
};

export type Ticker = { t: string; src: string; line: string };

export type KGEntity = {
  id: string;
  label: string;
  type: string;
  x: number;
  y: number;
  deg: number;
};

export type KGEdge = [string, string, string];

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

export const SOURCES: Source[] = [
  { id: "gdelt", name: "GDELT 2.0", type: "Geopolitics", status: "ok", latency: 1.2, errorRate: 0.001, lastUpdate: "00:00:03", coverage: "global", quality: 0.94 },
  { id: "reuters", name: "Reuters Connect", type: "News API", status: "ok", latency: 0.8, errorRate: 0.002, lastUpdate: "00:00:01", coverage: "global", quality: 0.97 },
  { id: "ap", name: "Associated Press", type: "News API", status: "ok", latency: 0.9, errorRate: 0.003, lastUpdate: "00:00:02", coverage: "global", quality: 0.96 },
  { id: "xinhua", name: "Xinhua RSS", type: "RSS", status: "ok", latency: 2.1, errorRate: 0.005, lastUpdate: "00:00:11", coverage: "CN, regional", quality: 0.81 },
  { id: "kyodo", name: "Kyodo News", type: "News API", status: "ok", latency: 1.4, errorRate: 0.001, lastUpdate: "00:00:04", coverage: "JP, regional", quality: 0.93 },
  { id: "cna", name: "CNA Taiwan", type: "RSS", status: "ok", latency: 1.6, errorRate: 0.002, lastUpdate: "00:00:08", coverage: "TW", quality: 0.91 },
  { id: "scmp", name: "SCMP", type: "RSS", status: "warn", latency: 4.8, errorRate: 0.022, lastUpdate: "00:00:42", coverage: "HK, CN", quality: 0.89 },
  { id: "ft", name: "Financial Times", type: "News API", status: "ok", latency: 1.1, errorRate: 0.001, lastUpdate: "00:00:06", coverage: "Markets, EU", quality: 0.96 },
  { id: "twitter", name: "X Firehose (sample)", type: "Social", status: "ok", latency: 0.4, errorRate: 0.012, lastUpdate: "00:00:00", coverage: "global", quality: 0.62 },
  { id: "weibo", name: "Weibo (translated)", type: "Social", status: "warn", latency: 6.2, errorRate: 0.041, lastUpdate: "00:01:14", coverage: "CN", quality: 0.58 },
  { id: "csis", name: "CSIS ChinaPower", type: "Research", status: "ok", latency: 12.0, errorRate: 0, lastUpdate: "02:14:00", coverage: "Indo-Pacific", quality: 0.98 },
  { id: "rand", name: "RAND Corp", type: "Research", status: "ok", latency: 18.0, errorRate: 0, lastUpdate: "06:22:00", coverage: "Defense", quality: 0.97 },
  { id: "imf", name: "IMF Bulletin", type: "Macro", status: "ok", latency: 9.0, errorRate: 0, lastUpdate: "01:08:00", coverage: "global", quality: 0.95 },
  { id: "marinetraffic", name: "MarineTraffic AIS", type: "Geo", status: "ok", latency: 0.6, errorRate: 0.004, lastUpdate: "00:00:00", coverage: "maritime", quality: 0.92 },
  { id: "flightradar", name: "Flightradar24", type: "Geo", status: "ok", latency: 0.5, errorRate: 0.002, lastUpdate: "00:00:00", coverage: "aviation", quality: 0.94 },
  { id: "planet", name: "Planet Labs (daily)", type: "Imagery", status: "down", latency: 0, errorRate: 1.0, lastUpdate: "08:42:00", coverage: "global", quality: 0.0 },
  { id: "acled", name: "ACLED", type: "Conflict", status: "ok", latency: 24.0, errorRate: 0, lastUpdate: "12:00:00", coverage: "global", quality: 0.96 },
  { id: "openstreetmap", name: "OSM Geocoder", type: "Geo", status: "ok", latency: 0.3, errorRate: 0.001, lastUpdate: "00:00:00", coverage: "global", quality: 0.99 },
];

export const EVENTS: GeoEvent[] = [
  { id: "e1", lat: 23.7, lon: 120.6, label: "Joint Sword 2026-A concludes", topic: "TW Strait", severity: 0.92, country: "TW" },
  { id: "e2", lat: 25.0, lon: 121.5, label: "Lai cabinet emergency convene", topic: "TW Strait", severity: 0.78, country: "TW" },
  { id: "e3", lat: 39.9, lon: 116.4, label: "Politburo standing committee session", topic: "TW Strait", severity: 0.81, country: "CN" },
  { id: "e4", lat: 35.7, lon: 139.7, label: "Diet emergency security session", topic: "TW Strait", severity: 0.73, country: "JP" },
  { id: "e5", lat: 38.9, lon: -77.0, label: "NSC principals meeting", topic: "TW Strait", severity: 0.69, country: "US" },
  { id: "e6", lat: 21.3, lon: -157.9, label: "INDOPACOM Status FOXTROT", topic: "TW Strait", severity: 0.84, country: "US" },
  { id: "e7", lat: 1.35, lon: 103.8, label: "MAS contingency liquidity facility", topic: "Markets", severity: 0.55, country: "SG" },
  { id: "e8", lat: 22.3, lon: 114.2, label: "HSBC USD swap line activated", topic: "Markets", severity: 0.61, country: "HK" },
  { id: "e9", lat: 24.8, lon: 120.9, label: "TSMC Hsinchu BCP drill", topic: "Supply Chain", severity: 0.66, country: "TW" },
  { id: "e10", lat: 33.4, lon: -112.1, label: "TSMC Arizona Fab 21 ramp", topic: "Supply Chain", severity: 0.41, country: "US" },
  { id: "e11", lat: 50.1, lon: 8.7, label: "ECB monitoring statement", topic: "Markets", severity: 0.32, country: "DE" },
  { id: "e12", lat: 51.5, lon: -0.1, label: "FCO summons PRC ambassador", topic: "Diplomatic", severity: 0.48, country: "GB" },
  { id: "e13", lat: 28.6, lon: 77.2, label: "MEA cautious statement", topic: "Diplomatic", severity: 0.22, country: "IN" },
  { id: "e14", lat: -33.9, lon: 151.2, label: "AUKUS pillar 2 emergency call", topic: "Defense", severity: 0.58, country: "AU" },
  { id: "e15", lat: 14.6, lon: 121.0, label: "EDCA bases on heightened alert", topic: "Defense", severity: 0.71, country: "PH" },
  { id: "e16", lat: 37.5, lon: 127.0, label: "ROK NSC convenes (private)", topic: "Diplomatic", severity: 0.44, country: "KR" },
  { id: "e17", lat: 55.7, lon: 37.6, label: "MID statement: 'Chinese internal'", topic: "Diplomatic", severity: 0.36, country: "RU" },
  { id: "e18", lat: 26.2, lon: 50.5, label: "Bahrain 5th Fleet readiness", topic: "Defense", severity: 0.29, country: "BH" },
  { id: "e19", lat: 13.0, lon: 80.2, label: "Chennai port LNG diversion", topic: "Markets", severity: 0.24, country: "IN" },
  { id: "e20", lat: 31.2, lon: 121.5, label: "Shanghai container backlog", topic: "Supply Chain", severity: 0.62, country: "CN" },
  { id: "e21", lat: 22.5, lon: 113.9, label: "Shenzhen export queue spike", topic: "Supply Chain", severity: 0.54, country: "CN" },
  { id: "e22", lat: 35.6, lon: 139.4, label: "Yokota Air Base ALERT-1", topic: "Defense", severity: 0.77, country: "JP" },
  { id: "e23", lat: 24.4, lon: 122.9, label: "Yonaguni JGSDF reinforcement", topic: "Defense", severity: 0.68, country: "JP" },
  { id: "e24", lat: -36.8, lon: 174.7, label: "NZ MFAT statement on freedom of navigation", topic: "Diplomatic", severity: 0.18, country: "NZ" },
];

export const HOTSPOTS: Hotspot[] = [
  { rank: 1, label: "Taiwan Strait", topic: "TW Strait", events24h: 1247, delta: "+312%", severity: 0.94 },
  { rank: 2, label: "Bashi Channel", topic: "TW Strait", events24h: 612, delta: "+411%", severity: 0.86 },
  { rank: 3, label: "Senkaku / Yonaguni", topic: "TW Strait", events24h: 308, delta: "+187%", severity: 0.71 },
  { rank: 4, label: "Spratly Islands", topic: "SCS", events24h: 142, delta: "+22%", severity: 0.42 },
  { rank: 5, label: "Korean Peninsula", topic: "DPRK", events24h: 98, delta: "+11%", severity: 0.38 },
  { rank: 6, label: "Red Sea", topic: "Houthis", events24h: 81, delta: "-4%", severity: 0.34 },
  { rank: 7, label: "Black Sea", topic: "UA/RU", events24h: 76, delta: "+2%", severity: 0.31 },
];

export const TICKER: Ticker[] = [
  { t: "14:22:08", src: "Reuters", line: "PLA Eastern Theater Cmd: 'Joint Sword' drills concluded; standing presence to continue" },
  { t: "14:22:01", src: "Kyodo", line: "JP MoD: 4 PLAN destroyers tracked 24nm S of Yonaguni" },
  { t: "14:21:55", src: "FT", line: "TWD weakens 1.4% intraday; NTD/USD touches 33.81" },
  { t: "14:21:48", src: "AP", line: "INDOPACOM: 'We have the capability and the will to respond'" },
  { t: "14:21:39", src: "Xinhua", line: "MoFA spokesperson: 'External interference will be met with countermeasures'" },
  { t: "14:21:31", src: "CNA", line: "MOFA-TW summons 17 ambassadors for briefing" },
  { t: "14:21:22", src: "MarineTraffic", line: "Container traffic Kaohsiung -18% vs 7d avg" },
  { t: "14:21:14", src: "X Firehose", line: "#TaiwanStrait trending; 412k posts/hr (peak)" },
  { t: "14:21:02", src: "GDELT", line: "Tone score Goldstein: -7.2 for CN-TW dyad (24h)" },
  { t: "14:20:51", src: "ACLED", line: "No kinetic events recorded in 72h window" },
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
  { id: "ja-sword", label: "Joint Sword 2026-A", type: "event", x: 0.18, y: 0.72, deg: 8 },
  { id: "asl", label: "Anti-Secession Law", type: "doc", x: 0.15, y: 0.32, deg: 6 },
  { id: "tra", label: "Taiwan Relations Act", type: "doc", x: 0.88, y: 0.22, deg: 7 },
  { id: "haikun", label: "ROCS Hai Kun", type: "asset", x: 0.62, y: 0.62, deg: 5 },
  { id: "bashi", label: "Bashi Channel", type: "place", x: 0.42, y: 0.78, deg: 9 },
  { id: "yonaguni", label: "Yonaguni Island", type: "place", x: 0.7, y: 0.42, deg: 6 },
  { id: "fab18", label: "TSMC Fab 18 (N3)", type: "asset", x: 0.4, y: 0.78, deg: 4 },
  { id: "fab21", label: "TSMC Arizona Fab 21", type: "asset", x: 0.92, y: 0.6, deg: 3 },
];

export const KG_EDGES: KGEdge[] = [
  ["lai", "tw", "leads"],
  ["xi", "cn", "leads"],
  ["cn", "tw", "claims"],
  ["us", "tw", "supports"],
  ["jp", "tw", "linked-to"],
  ["pla", "cn", "part-of"],
  ["indopacom", "us", "part-of"],
  ["pla", "ja-sword", "executed"],
  ["ja-sword", "tw", "targets"],
  ["xi", "asl", "invokes"],
  ["us", "tra", "obligated-by"],
  ["tw", "haikun", "operates"],
  ["pla", "bashi", "transits"],
  ["bashi", "tw", "borders"],
  ["yonaguni", "jp", "part-of"],
  ["tsmc", "tw", "headquartered"],
  ["tsmc", "fab18", "operates"],
  ["tsmc", "fab21", "operates"],
  ["fab18", "tw", "located"],
  ["fab21", "us", "located"],
  ["lai", "xi", "opposes"],
  ["indopacom", "pla", "deters"],
  ["jp", "yonaguni", "garrisons"],
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
  { id: "d-2026-04-23-01", title: "Sahel withdrawal: French strategic redirection", time: "2d", personas: 4, status: "done" },
  { id: "d-2026-04-22-03", title: "Houthi maritime activity — insurance market", time: "2d", personas: 5, status: "done" },
  { id: "d-2026-04-21-05", title: "DPRK 7th nuclear test: regional response", time: "3d", personas: 6, status: "done" },
  { id: "d-2026-04-20-02", title: "Argentina IMF tranche: Milei orthodoxy stress test", time: "4d", personas: 4, status: "done" },
];

export const TRENDING: string[] = [
  "Will PLA escalate to quarantine in next 90 days?",
  "Senkaku flashpoint probability if TW activates conscripts?",
  "TSMC Arizona ramp: leading-edge by Q4 2026?",
  "Fed reaction function to TW-driven equity shock?",
  "Does AUKUS pillar 2 deliver before 2027?",
  "Russia–DPRK arms flow: end-state by year end?",
];

export const ARGUS_DATA = {
  PERSONAS,
  SOURCES,
  EVENTS,
  HOTSPOTS,
  TICKER,
  KG_ENTITIES,
  KG_EDGES,
  ORCHESTRATION,
  RECENT,
  TRENDING,
};
