import {
  LayoutDashboard,
  ChartNoAxesCombined,
  Database,
  FileText,
  Settings,
  ChevronRight,
  User
} from "lucide-react";  
interface SidebarProps {
  activePage: string;
  onNavigate: (page: string) => void;
}

function Sidebar({ activePage, onNavigate }: SidebarProps) {

  const menuItems = [
    {
      name: "Dashboard",
      icon: LayoutDashboard
    },
    {
      name: "Analytics",
      icon: ChartNoAxesCombined
    },
    {
      name: "Data Explorer",
      icon: Database
    },
    {
      name: "Reports",
      icon: FileText
    }
  ];

  return (
    <aside className="sidebar">

      <div className="sidebar-logo">
        <div className="logo-icon">
          <ChartNoAxesCombined size={23} />
        </div>

        <h2>BI Analytics</h2>
      </div>

      <div className="sidebar-section">
        <p className="sidebar-label">WORKSPACE</p>

        <nav className="sidebar-menu">
          {menuItems.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.name}
                className={`sidebar-link ${
                  activePage === item.name ? "active" : ""
                }`}
                onClick={() => onNavigate(item.name)}
              >
                <Icon size={19} />

                <span>{item.name}</span>

                {activePage === item.name && (
                  <ChevronRight size={16} className="menu-arrow" />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="sidebar-bottom">

        <p className="sidebar-label">PREFERENCES</p>

        <button
          className={`sidebar-link ${
            activePage === "Settings" ? "active" : ""
          }`}
          onClick={() => onNavigate("Settings")}
        >
          <Settings size={19} />
          <span>Settings</span>
        </button>

        <div className="sidebar-profile">
          <div className="profile-avatar">
            <User size={20} />
          </div>

          <div className="profile-info">
            <strong>BI Analyst</strong>
            <span>Workspace User</span>
          </div>
        </div>

      </div>

    </aside>
  );
}

export default Sidebar;