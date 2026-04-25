// argus — main app: routing, theme, tweaks, keyboard
const { useState: uA, useEffect: uB, useMemo: uC, useRef: uD } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "dark",
  "density": "comfortable",
  "showCRT": false,
  "animSpeed": 1,
  "accent": "#f5a524"
}/*EDITMODE-END*/;

function App() {
  const [route, setRoute] = uA("home");
  const [theme, setTheme] = uA("dark");
  const [lightVariant, setLightVariant] = uA("paper");
  const [cmdOpen, setCmdOpen] = uA(false);
  const [notifsOpen, setNotifsOpen] = uA(false);
  const [collapsed, setCollapsed] = uA(false);
  const [debateState, setDebateState] = uA({ idx: 0, topic: "" });
  const [tweaks, setTweaks] = useTweaks ? useTweaks(TWEAK_DEFAULTS) : [TWEAK_DEFAULTS, () => {}];

  // Apply theme
  uB(() => {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.setAttribute("data-light-variant", lightVariant);
  }, [theme, lightVariant]);

  // Keyboard shortcuts
  uB(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCmdOpen(true);
      }
      if (e.key === "Escape") {
        setCmdOpen(false); setNotifsOpen(false);
      }
      // F1-F12
      const fnMap = { F1: "home", F2: "world", F3: "kg", F4: "ops", F5: "personas", F6: "debate", F7: "synthesis", F8: "library", F9: "replay", F10: "compare", F11: "sources", F12: "obs" };
      if (fnMap[e.key]) { e.preventDefault(); setRoute(fnMap[e.key]); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const launchDebate = (topic) => {
    setDebateState({ idx: 0, topic });
  };

  let screen = null;
  switch (route) {
    case "home":      screen = <HomeScreen setRoute={setRoute} launchDebate={launchDebate} />; break;
    case "world":     screen = <WorldView setRoute={setRoute} launchDebate={launchDebate} />; break;
    case "kg":        screen = <KGScreen />; break;
    case "ops":       screen = <OpsTheater setRoute={setRoute} debateState={debateState} />; break;
    case "personas":  screen = <PersonaDesigner />; break;
    case "debate":    screen = <DebateRoom setRoute={setRoute} debateState={debateState} setDebateState={setDebateState} />; break;
    case "synthesis": screen = <SynthesisView setRoute={setRoute} />; break;
    case "library":   screen = <LibraryScreen setRoute={setRoute} />; break;
    case "replay":    screen = <ReplayScreen />; break;
    case "compare":   screen = <CompareScreen />; break;
    case "sources":   screen = <SourcesScreen />; break;
    case "obs":       screen = <ObsScreen />; break;
    case "settings":  screen = <SettingsScreen />; break;
    default:          screen = <HomeScreen setRoute={setRoute} launchDebate={launchDebate} />;
  }

  return (
    <div className="col" style={{ height: "100vh", width: "100vw", overflow: "hidden", background: "var(--bg-0)" }}>
      <TopBar openCmd={() => setCmdOpen(true)} theme={theme} setTheme={setTheme} notifs={notifsOpen} setNotifs={setNotifsOpen} />
      <div className="row grow" style={{ overflow: "hidden" }}>
        <Sidebar route={route} setRoute={setRoute} collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
        <div className="grow col" style={{ overflow: "hidden", position: "relative" }}>
          {screen}
        </div>
      </div>
      <StatusBar route={route} theme={theme} />
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} setRoute={setRoute} />
      <NotifsPanel open={notifsOpen} onClose={() => setNotifsOpen(false)} />
      <ArgusTweaks theme={theme} setTheme={setTheme} lightVariant={lightVariant} setLightVariant={setLightVariant} debateState={debateState} setDebateState={setDebateState} />
    </div>
  );
}

// Custom Tweaks panel — uses TweaksPanel from starter
function ArgusTweaks({ theme, setTheme, lightVariant, setLightVariant, debateState, setDebateState }) {
  if (typeof TweaksPanel === "undefined") return null;
  return (
    <TweaksPanel title="argus · TWEAKS">
      <TweakSection title="Theme">
        <TweakRadio label="Mode" value={theme} options={[{value:"dark",label:"Dark"},{value:"light",label:"Light"}]} onChange={setTheme} />
        {theme === "light" && (
          <TweakRadio label="Light palette" value={lightVariant} options={[
            {value:"paper", label:"Paper · warm sepia"},
            {value:"cool",  label:"Cool · clinical bluish-grey"},
            {value:"ledger",label:"Ledger · pure white"},
          ]} onChange={setLightVariant} />
        )}
      </TweakSection>
      <TweakSection title="Debate Playback">
        <div style={{ padding: "6px 0" }}>
          <Btn primary style={{ width: "100%" }} onClick={() => setDebateState({ idx: 0, topic: "" })}>↺ Restart debate</Btn>
        </div>
        <div style={{ padding: "6px 0" }}>
          <Btn ghost style={{ width: "100%" }} onClick={() => setDebateState(s => ({ ...s, idx: window.ARGUS_DATA.TRANSCRIPT.length }))}>⏭ Skip to end</Btn>
        </div>
      </TweakSection>
      <TweakSection title="Keyboard">
        <div style={{ fontSize: 10, color: "var(--ink-2)", lineHeight: 1.7, padding: "4px 0" }}>
          <div><span className="amber">⌘K</span> · command palette</div>
          <div><span className="amber">F1–F12</span> · jump to screen</div>
          <div><span className="amber">ESC</span> · close overlay</div>
        </div>
      </TweakSection>
    </TweaksPanel>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
