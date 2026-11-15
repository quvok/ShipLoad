import { useState } from "react";

type NavKey = "overview" | "vessels" | "documents" | "loading" | "reports";

const navigation: { key: NavKey; label: string; icon: string }[] = [
  { key: "overview", label: "Обзор", icon: "◫" },
  { key: "vessels", label: "Суда", icon: "▤" },
  { key: "documents", label: "Документы", icon: "▧" },
  { key: "loading", label: "Загрузочные условия", icon: "⌁" },
  { key: "reports", label: "Расчёты", icon: "▥" },
];

function App() {
  const [active, setActive] = useState<NavKey>("overview");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">S</span><span>ShipLoad<small>РАБОЧЕЕ МЕСТО СУДНА</small></span></div>
        <div className="workspace-label">РАБОЧАЯ ОБЛАСТЬ</div>
        <nav>
          {navigation.map((item) => (
            <button key={item.key} className={active === item.key ? "nav-item active" : "nav-item"} onClick={() => setActive(item.key)}>
              <span className="nav-icon">{item.icon}</span>{item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection"><span /> Локальная версия проекта</div>
          <div className="user-row"><div className="avatar">S</div><div>Владелец проекта<small>Разработка ShipLoad</small></div></div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div><span className="breadcrumb">Рабочая область</span><span className="slash">/</span><strong>{navigation.find((item) => item.key === active)?.label}</strong></div>
          <div className="topbar-right"><span className="env-tag">РАЗРАБОТКА</span><button className="help-button">Документация ↗</button></div>
        </header>

        <section className="content">
          <div className="page-heading">
            <div><div className="eyebrow">СУДОВОЖДЕНИЕ / ИНЖЕНЕРНЫЕ РАСЧЁТЫ</div><h1>{active === "overview" ? "Рабочая область судна" : navigation.find((item) => item.key === active)?.label}</h1><p>Управление данными судна, проверка судовой документации и подготовка загрузочных условий.</p></div>
            <button className="primary-button" onClick={() => setActive("vessels")}>＋ Добавить судно</button>
          </div>

          <div className="notice"><span className="notice-icon">!</span><div><strong>Тестовая версия — не допущена к эксплуатации</strong><p>Расчёты остойчивости и загрузки пока не реализованы. Не используйте приложение для принятия решений, влияющих на безопасность судна.</p></div></div>

          <div className="metric-grid">
            <Metric label="СУДА" value="0" detail="Профили судов ещё не созданы" />
            <Metric label="СУДОВЫЕ ДОКУМЕНТЫ" value="0" detail="Ожидается первая загрузка" />
            <Metric label="ЗАГРУЗОЧНЫЕ УСЛОВИЯ" value="0" detail="Условия загрузки не созданы" />
            <Metric label="ПРОВЕРЕННЫЕ РАСЧЁТЫ" value="0" detail="Эталонные случаи не настроены" />
          </div>

          <div className="section-grid">
            <section className="panel getting-started">
              <div className="panel-heading"><div><div className="eyebrow">НАЧАЛО РАБОТЫ</div><h2>Настройка первого судна</h2></div><span className="step-count">0 / 4</span></div>
              <SetupStep number="01" title="Создать профиль судна" description="Указать главные размерения, систему координат и исходные плоскости отсчёта." />
              <SetupStep number="02" title="Загрузить судовую документацию" description="Добавить информацию об остойчивости, гидростатические таблицы и таблицы калибровки танков." />
              <SetupStep number="03" title="Проверить распознанные данные" description="Сверить каждое импортированное значение с исходной страницей и таблицей." />
              <SetupStep number="04" title="Сформировать загрузочное условие" description="Добавить массу порожнего судна, груз, судовые запасы, балласт и прочие переменные нагрузки." />
              <button className="secondary-button" onClick={() => setActive("vessels")}>Перейти к настройке судна <span>→</span></button>
            </section>
            <section className="panel status-panel">
              <div className="eyebrow">СОСТОЯНИЕ СИСТЕМЫ</div><h2>Расчётные модули</h2>
              <StatusRow name="База данных судов" status="Не настроена" />
              <StatusRow name="Распознавание документов" status="Не реализовано" />
              <StatusRow name="Гидростатические расчёты" status="Не реализованы" />
              <StatusRow name="Проверка критериев остойчивости" status="Не реализована" />
              <StatusRow name="Формирование отчётов" status="Не реализовано" />
              <div className="status-foot">Модули будут доступны после выполнения требований к проверке и подтверждению данных.</div>
            </section>
          </div>

          <div className="bottom-note"><span>SHIPLOAD</span><span>Прослеживаемость данных · Повторяемость расчётов · Явный статус проверки</span><span>v0.1.0</span></div>
        </section>
      </main>
    </div>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="metric-card"><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>;
}

function SetupStep({ number, title, description }: { number: string; title: string; description: string }) {
  return <div className="setup-step"><span className="step-number">{number}</span><div><strong>{title}</strong><p>{description}</p></div><span className="step-arrow">→</span></div>;
}

function StatusRow({ name, status }: { name: string; status: string }) {
  return <div className="status-row"><span className="status-dot" /><span>{name}</span><small>{status}</small></div>;
}

export default App;
