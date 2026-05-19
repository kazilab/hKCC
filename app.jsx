// hKCC main app — routing + tweaks integration

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "paper",
  "accent": "#8B2E2A",
  "density": "comfortable",
  "matrixStyle": "heatmap",
  "serifHeadings": true
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = window.useTweaks(TWEAK_DEFAULTS);
  const [route, setRoute] = useState({ screen: "home" });

  const onNav = (screen, opts = {}) => {
    setRoute({ screen, ...opts });
    window.scrollTo({ top: 0, behavior: "instant" });
  };

  // Apply tweak side-effects
  useEffect(() => {
    document.documentElement.dataset.theme = t.theme === "dark" ? "dark" : "paper";
    document.documentElement.dataset.density = t.density;
    if (t.accent) {
      document.documentElement.style.setProperty("--accent", t.accent);
      document.documentElement.style.setProperty("--accent-hover", shade(t.accent, -20));
      document.documentElement.style.setProperty("--accent-soft", mix(t.accent, "#F7F4ED", 0.85));
    }
    if (!t.serifHeadings) {
      document.documentElement.style.setProperty("--font-serif", `"Public Sans", system-ui, sans-serif`);
    } else {
      document.documentElement.style.setProperty("--font-serif", `"Instrument Serif", "Times New Roman", serif`);
    }
  }, [t.theme, t.accent, t.density, t.serifHeadings]);

  // Resolve screen
  let screenEl = null;
  switch (route.screen) {
    case "home": screenEl = <window.ScreenHome onNav={onNav} />; break;
    case "kccs": screenEl = <window.ScreenKCCs onNav={onNav} />; break;
    case "kccDetail": screenEl = <window.ScreenKCCDetail id={route.id} onNav={onNav} />; break;
    case "carcinogens": screenEl = <window.ScreenCarcinogens onNav={onNav} />; break;
    case "carcDetail": screenEl = <window.ScreenCarcDetail id={route.id} onNav={onNav} />; break;
    case "matrix": screenEl = <window.ScreenMatrix onNav={onNav} matrixStyle={t.matrixStyle} />; break;
    case "assays": screenEl = <window.ScreenAssays onNav={onNav} />; break;
    case "literature": screenEl = <window.ScreenLiterature onNav={onNav} />; break;
    case "api": screenEl = <window.ScreenAPI onNav={onNav} />; break;
    case "about": screenEl = <window.ScreenAbout onNav={onNav} />; break;
    default: screenEl = <window.ScreenHome onNav={onNav} />;
  }

  const { TweaksPanel, TweakSection, TweakRadio, TweakColor, TweakToggle } = window;

  return (
    <div className="app">
      <Sidebar route={route} onNav={onNav} tweaks={t} />
      <main className="main">
        <Topbar route={route} onNav={onNav} />
        {screenEl}
      </main>

      <TweaksPanel title="Tweaks">
        <TweakSection label="Appearance" />
        <TweakRadio label="Theme" value={t.theme}
                    options={["paper", "dark"]}
                    onChange={v => setTweak("theme", v)} />
        <TweakColor label="Accent" value={t.accent}
                    options={["#8B2E2A", "#2D5959", "#1E3A8A", "#7A4019"]}
                    onChange={v => setTweak("accent", v)} />
        <TweakToggle label="Serif headings" value={t.serifHeadings}
                     onChange={v => setTweak("serifHeadings", v)} />

        <TweakSection label="Layout" />
        <TweakRadio label="Density" value={t.density}
                    options={["comfortable", "compact"]}
                    onChange={v => setTweak("density", v)} />

        <TweakSection label="Evidence matrix" />
        <TweakRadio label="Style" value={t.matrixStyle}
                    options={["heatmap", "dot", "bar", "number"]}
                    onChange={v => setTweak("matrixStyle", v)} />
      </TweaksPanel>
    </div>
  );
}

// Color helpers
function hexToRgb(h) {
  if (!h || typeof h !== "string") return [0, 0, 0];
  const m = h.replace("#", "");
  return [parseInt(m.slice(0,2), 16), parseInt(m.slice(2,4), 16), parseInt(m.slice(4,6), 16)];
}
function rgbToHex([r,g,b]) {
  return "#" + [r,g,b].map(x => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, "0")).join("");
}
function shade(hex, amt) {
  const rgb = hexToRgb(hex).map(x => x + amt);
  return rgbToHex(rgb);
}
function mix(a, b, t) {
  const ra = hexToRgb(a), rb = hexToRgb(b);
  return rgbToHex(ra.map((x, i) => x * (1 - t) + rb[i] * t));
}

window.App = App;
ReactDOM.createRoot(document.getElementById("root")).render(<App />);
