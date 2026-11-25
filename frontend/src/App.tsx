
import { useState } from "react";
import Sidebar from "./components/Sidebar";

function App() {

  const [activePage, setActivePage] = useState("Dashboard");

  return (
    <div className="app-layout">

      <Sidebar
        activePage={activePage}
        onNavigate={setActivePage}
      />

      <main className="main-content">

        <header className="top-header">
          <h2>{activePage}</h2>
          <span>Welcome to BI Analytics</span>
        </header>

        <section className="page-content">
          <h1>{activePage}</h1>

          <p>
            Welcome to your Business Intelligence
            and Data Analytics platform.
          </p>
        </section>

      </main>

    </div>
  );
}

export default App;
