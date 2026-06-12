import { data } from "./data";
import { href, useHashRoute } from "./lib/util";
import Overview from "./pages/Overview";
import Matrix from "./pages/Matrix";
import Carcinogens from "./pages/Carcinogens";
import AgentDetail from "./pages/AgentDetail";
import Kccs from "./pages/Kccs";
import KccDetail from "./pages/KccDetail";
import Assays from "./pages/Assays";
import AssayDetail from "./pages/AssayDetail";
import Methodology from "./pages/Methodology";
import About from "./pages/About";

const NAV = [
  { path: "", label: "Overview" },
  { path: "matrix", label: "Matrix" },
  { path: "carcinogens", label: "Carcinogens" },
  { path: "kccs", label: "KCCs" },
  { path: "assays", label: "Assays" },
  { path: "methodology", label: "Methodology" },
  { path: "about", label: "About" },
];

export default function App() {
  const [parts, navigate] = useHashRoute();
  const root = parts[0] ?? "";

  function render() {
    switch (root) {
      case "":
        return <Overview navigate={navigate} />;
      case "matrix":
        return <Matrix navigate={navigate} />;
      case "carcinogens":
        return parts[1] ? <AgentDetail id={parts[1]} navigate={navigate} /> : <Carcinogens navigate={navigate} />;
      case "kccs":
        return parts[1] ? <KccDetail id={parts[1]} navigate={navigate} /> : <Kccs navigate={navigate} />;
      case "assays":
        return parts[1] ? <AssayDetail id={parts[1]} navigate={navigate} /> : <Assays navigate={navigate} />;
      case "methodology":
        return <Methodology />;
      case "about":
        return <About />;
      default:
        return (
          <div className="card" style={{ marginTop: 40 }}>
            <h2>Not found</h2>
            <a href={href("")}>← Back to overview</a>
          </div>
        );
    }
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <a href={href("")} className="brand" style={{ textDecoration: "none" }}>
            hKCC<small>v{data.meta.version}</small>
          </a>
          <nav className="nav">
            {NAV.map((n) => (
              <a key={n.path} href={href(n.path)} className={root === n.path ? "active" : ""}>
                {n.label}
              </a>
            ))}
          </nav>
        </div>
      </header>
      <main className="app">
        {render()}
        <footer className="footer">
          <strong>hKCC</strong> — Key Characteristics of Human Carcinogens · v{data.meta.version} ·
          generated {data.meta.generated}
          <br />
          {data.meta.developer} · {data.meta.contact} · data CC-BY-4.0 · code MIT · offline single-file build
        </footer>
      </main>
    </>
  );
}
