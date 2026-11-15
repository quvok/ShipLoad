import { useCallback, useEffect, useState, type FormEvent } from "react";

type NavKey = "overview" | "vessels" | "documents" | "loading" | "reports";
type VesselType = "general_cargo" | "container" | "bulk_carrier" | "tanker" | "multipurpose" | "other";
type Vessel = {
  id: string; name: string; vessel_type: VesselType; loa_m: number; lbp_m: number;
  moulded_breadth_m: number; moulded_depth_m: number; data_status: string; created_at: string;
};
const navigation: { key: NavKey; label: string; icon: string }[] = [
  { key: "overview", label: "Обзор", icon: "◫" }, { key: "vessels", label: "Суда", icon: "▤" },
  { key: "documents", label: "Документы", icon: "▧" }, { key: "loading", label: "Загрузочные условия", icon: "⌁" },
  { key: "reports", label: "Расчёты", icon: "▥" },
];
const vesselTypes: { value: VesselType; label: string }[] = [
  { value: "general_cargo", label: "Генеральный груз" }, { value: "container", label: "Контейнеровоз" },
  { value: "bulk_carrier", label: "Балкер" }, { value: "tanker", label: "Танкер" },
  { value: "multipurpose", label: "Многоцелевое судно" }, { value: "other", label: "Другое" },
];
const API = "/api/v1";

function App() {
  const [active, setActive] = useState<NavKey>("overview");
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [apiState, setApiState] = useState<"checking" | "online" | "offline">("checking");
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadVessels = useCallback(async () => {
    setApiState("checking");
    try {
      const response = await fetch(`${API}/vessels`);
      if (!response.ok) throw new Error("Не удалось получить список судов.");
      const data = await response.json() as Vessel[];
      setVessels(data);
      setApiState("online");
    } catch {
      setApiState("offline");
    }
  }, []);

  useEffect(() => { void loadVessels(); }, [loadVessels]);

  async function createVessel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSuccess(""); setLoading(true);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      name: String(form.get("name") ?? "").trim(),
      vessel_type: form.get("vessel_type"),
      loa_m: Number(form.get("loa_m")), lbp_m: Number(form.get("lbp_m")),
      moulded_breadth_m: Number(form.get("moulded_breadth_m")),
      moulded_depth_m: Number(form.get("moulded_depth_m")),
      coordinate_convention: {
        origin_description: String(form.get("origin_description") ?? "").trim(),
        x_axis_direction: form.get("x_axis_direction"), y_axis_direction: form.get("y_axis_direction"),
        z_axis_direction: form.get("z_axis_direction"),
        vertical_datum_description: String(form.get("vertical_datum_description") ?? "").trim(),
      },
    };
    try {
      const response = await fetch(`${API}/vessels`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = body?.detail;
        throw new Error(typeof detail === "string" ? detail : "Проверьте введённые данные. Сервер отклонил запрос.");
      }
      await loadVessels(); setShowForm(false); setSuccess("Профиль судна сохранён в локальной базе данных.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка при сохранении судна.");
    } finally { setLoading(false); }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">S</span><span>ShipLoad<small>РАБОЧЕЕ МЕСТО СУДНА</small></span></div>
        <div className="workspace-label">РАБОЧАЯ ОБЛАСТЬ</div>
        <nav>{navigation.map((item) => <button key={item.key} className={active === item.key ? "nav-item active" : "nav-item"} onClick={() => setActive(item.key)}><span className="nav-icon">{item.icon}</span>{item.label}</button>)}</nav>
        <div className="sidebar-bottom">
          <div className="connection"><span className={apiState === "online" ? "connection-dot online" : "connection-dot"} />{apiState === "online" ? "Локальная база подключена" : apiState === "checking" ? "Проверка подключения…" : "API не подключён"}</div>
          <div className="user-row"><div className="avatar">S</div><div>Локальный проект<small>Разработка ShipLoad</small></div></div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar"><div><span className="breadcrumb">Рабочая область</span><span className="slash">/</span><strong>{navigation.find((item) => item.key === active)?.label}</strong></div><div className="topbar-right"><span className="env-tag">РАЗРАБОТКА</span><a className="help-button" href="https://github.com/quvok/ShipLoad" target="_blank" rel="noreferrer">Репозиторий ↗</a></div></header>
        <section className="content">
          {active === "loading" ? (<LoadingPage vessels={vessels} apiState={apiState} />) : active === "vessels" ? (
            <VesselsPage vessels={vessels} apiState={apiState} showForm={showForm} setShowForm={setShowForm}
              onSubmit={createVessel} loading={loading} error={error} success={success} onRefresh={loadVessels} />
          ) : (
            <>
              <div className="page-heading"><div><div className="eyebrow">СУДОВОЖДЕНИЕ / ИНЖЕНЕРНЫЕ РАСЧЁТЫ</div><h1>{active === "overview" ? "Рабочая область судна" : navigation.find((item) => item.key === active)?.label}</h1><p>Управление данными судна, проверка судовой документации и подготовка загрузочных условий.</p></div><button className="primary-button" onClick={() => { setActive("vessels"); setShowForm(true); }}>＋ Добавить судно</button></div>
              <div className="notice"><span className="notice-icon">!</span><div><strong>Тестовая версия — не допущена к эксплуатации</strong><p>Расчёты остойчивости и загрузки пока не реализованы. Не используйте приложение для принятия решений, влияющих на безопасность судна.</p></div></div>
              <div className="metric-grid">
                <Metric label="СУДА" value={String(vessels.length)} detail={vessels.length ? "Профили в локальной базе" : "Профили судов ещё не созданы"} />
                <Metric label="СУДОВЫЕ ДОКУМЕНТЫ" value="0" detail="Ожидается первая загрузка" />
                <Metric label="ЗАГРУЗОЧНЫЕ УСЛОВИЯ" value="0" detail="Условия загрузки не созданы" />
                <Metric label="ПРОВЕРЕННЫЕ РАСЧЁТЫ" value="0" detail="Эталонные случаи не настроены" />
              </div>
              <div className="section-grid">
                <section className="panel getting-started"><div className="panel-heading"><div><div className="eyebrow">НАЧАЛО РАБОТЫ</div><h2>Настройка первого судна</h2></div><span className="step-count">{vessels.length ? "1" : "0"} / 4</span></div>
                  <SetupStep number="01" title="Создать профиль судна" description="Указать главные размерения, систему координат и исходные плоскости отсчёта." />
                  <SetupStep number="02" title="Загрузить судовую документацию" description="Добавить информацию об остойчивости, гидростатические таблицы и таблицы калибровки танков." />
                  <SetupStep number="03" title="Проверить распознанные данные" description="Сверить каждое импортированное значение с исходной страницей и таблицей." />
                  <SetupStep number="04" title="Сформировать загрузочное условие" description="Добавить массу порожнего судна, груз, судовые запасы, балласт и прочие переменные нагрузки." />
                  <button className="secondary-button" onClick={() => setActive("vessels")}>Перейти к настройке судна <span>→</span></button>
                </section>
                <section className="panel status-panel"><div className="eyebrow">СОСТОЯНИЕ СИСТЕМЫ</div><h2>Расчётные модули</h2>
                  <StatusRow name="Локальная база данных" status={apiState === "online" ? "Подключена" : apiState === "checking" ? "Проверка" : "Нет подключения"} />
                  <StatusRow name="Распознавание документов" status="Не реализовано" /><StatusRow name="Гидростатические расчёты" status="Не реализованы" /><StatusRow name="Проверка критериев остойчивости" status="Не реализована" /><StatusRow name="Формирование отчётов" status="Не реализовано" />
                  <div className="status-foot">Модули будут доступны после выполнения требований к проверке и подтверждению данных.</div>
                </section>
              </div>
            </>
          )}
          <div className="bottom-note"><span>SHIPLOAD</span><span>Прослеживаемость данных · Повторяемость расчётов · Явный статус проверки</span><span>v0.3.0</span></div>
        </section>
      </main>
    </div>
  );
}

function VesselsPage({ vessels, apiState, showForm, setShowForm, onSubmit, loading, error, success, onRefresh }: {
  vessels: Vessel[]; apiState: "checking" | "online" | "offline"; showForm: boolean;
  setShowForm: (value: boolean) => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  loading: boolean; error: string; success: string; onRefresh: () => void;
}) {
  return <><div className="page-heading"><div><div className="eyebrow">РЕЕСТР ФЛОТА</div><h1>Суда</h1><p>Паспорта судов и исходные системы координат. Все значения вводятся по судовой документации.</p></div><button className="primary-button" onClick={() => setShowForm(!showForm)}>{showForm ? "Закрыть форму" : "＋ Добавить судно"}</button></div>
    <div className="notice"><span className="notice-icon">!</span><div><strong>Статус профиля — черновик</strong><p>Создание профиля не подтверждает достоверность размерений. Перед любыми расчётами данные должны быть сверены с утверждёнными судовыми документами.</p></div></div>
    {apiState === "offline" && <div className="inline-alert error">Нет связи с API. Запустите backend локально: <code>uvicorn app.main:app --reload</code> из каталога backend. Данные пока не загружаются.</div>}
    {success && <div className="inline-alert success">{success}</div>}{error && <div className="inline-alert error">{error}</div>}
    {showForm && <section className="panel vessel-form-panel"><div className="panel-heading"><div><div className="eyebrow">НОВАЯ ЗАПИСЬ</div><h2>Основные характеристики судна</h2></div></div>
      <form onSubmit={onSubmit}>
        <div className="form-grid">
          <label>Название судна<input name="name" required maxLength={120} placeholder="Например, название по судовым документам" /></label>
          <label>Тип судна<select name="vessel_type" required defaultValue="general_cargo">{vesselTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select></label>
          <label>Длина наибольшая (LOA), м<input name="loa_m" type="number" min="0.01" max="1000" step="0.001" required /></label>
          <label>Длина между перпендикулярами (LBP), м<input name="lbp_m" type="number" min="0.01" max="1000" step="0.001" required /></label>
          <label>Теоретическая ширина (B), м<input name="moulded_breadth_m" type="number" min="0.01" max="250" step="0.001" required /></label>
          <label>Теоретическая высота борта (D), м<input name="moulded_depth_m" type="number" min="0.01" max="150" step="0.001" required /></label>
        </div>
        <div className="form-subheading">Система координат и плоскости отсчёта</div>
        <p className="form-hint">Выберите направления строго по принятой в документации системе координат. Не используйте значения по умолчанию без проверки.</p>
        <div className="form-grid">
          <label>Начало координат<input name="origin_description" required minLength={5} maxLength={500} placeholder="Точное описание точки начала координат" /></label>
          <label>Вертикальная плоскость / datum<input name="vertical_datum_description" required minLength={3} maxLength={500} placeholder="Например, baseline — если так указано в документации" /></label>
          <AxisSelect name="x_axis_direction" label="Направление оси X" options={[["positive_forward","Вперёд"],["positive_aft","В корму"]]} />
          <AxisSelect name="y_axis_direction" label="Направление оси Y" options={[["positive_port","На левый борт"],["positive_starboard","На правый борт"]]} />
          <AxisSelect name="z_axis_direction" label="Направление оси Z" options={[["positive_up","Вверх"],["positive_down","Вниз"]]} />
        </div>
        <div className="form-actions"><button type="button" className="secondary-button" onClick={() => setShowForm(false)}>Отмена</button><button className="primary-button" type="submit" disabled={loading || apiState !== "online"}>{loading ? "Сохранение…" : "Сохранить черновик"}</button></div>
      </form>
    </section>}
    <section className="panel vessel-list"><div className="panel-heading"><div><div className="eyebrow">ЛОКАЛЬНАЯ БАЗА ДАННЫХ</div><h2>Зарегистрированные суда</h2></div><button className="secondary-button" onClick={onRefresh}>Обновить</button></div>
      {vessels.length === 0 ? <div className="empty-state"><div className="empty-icon">▤</div><strong>Список судов пуст</strong><p>Создайте первый профиль. Запись будет сохранена в локальной SQLite-базе backend.</p></div> :
        <div className="vessel-table-wrap"><table className="vessel-table"><thead><tr><th>Название</th><th>Тип</th><th>LOA × B, м</th><th>LBP, м</th><th>Статус данных</th></tr></thead><tbody>{vessels.map((vessel) => <tr key={vessel.id}><td><strong>{vessel.name}</strong><small>{vessel.id}</small></td><td>{vesselTypes.find((type) => type.value === vessel.vessel_type)?.label ?? vessel.vessel_type}</td><td>{vessel.loa_m} × {vessel.moulded_breadth_m}</td><td>{vessel.lbp_m}</td><td><span className="draft-tag">{vessel.data_status}</span></td></tr>)}</tbody></table></div>}
    </section>
  </>;
}

type LoadingSummary = { id: string; name: string; vessel_data_revision: string; status: string; item_count: number; created_at: string };
function LoadingPage({ vessels, apiState }: { vessels: Vessel[]; apiState: "checking" | "online" | "offline" }) {
  const [vesselId, setVesselId] = useState("");
  const [records, setRecords] = useState<LoadingSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [itemRows, setItemRows] = useState<number[]>([0]);
  const [nextItemRow, setNextItemRow] = useState(1);
  useEffect(() => {
    if (!vesselId) { setRecords([]); return; }
    let cancelled = false;
    fetch(`${API}/vessels/${encodeURIComponent(vesselId)}/loading-conditions`)
      .then(async response => {
        if (!response.ok) throw new Error("Не удалось получить загрузочные условия.");
        return await response.json() as LoadingSummary[];
      })
      .then(data => { if (!cancelled) setRecords(data); })
      .catch(cause => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Ошибка загрузки."); });
    return () => { cancelled = true; };
  }, [vesselId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setNotice(""); setBusy(true);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      vessel_id: vesselId,
      name: String(form.get("condition_name") ?? "").trim(),
      vessel_data_revision: String(form.get("revision") ?? "").trim(),
      notes: String(form.get("notes") ?? "").trim() || null,
      items: itemRows.map(index => ({
        item_id: String(form.get(`item_id_${index}`) ?? "").trim(),
        description: String(form.get(`description_${index}`) ?? "").trim(),
        kind: form.get(`kind_${index}`),
        mass_kg: Number(form.get(`mass_kg_${index}`)),
        position: {
          x_m: Number(form.get(`x_m_${index}`)),
          y_m: Number(form.get(`y_m_${index}`)),
          z_m: Number(form.get(`z_m_${index}`)),
          position_source: String(form.get(`position_source_${index}`) ?? "").trim(),
        },
        source_reference: String(form.get(`source_reference_${index}`) ?? "").trim(),
      })),
    };
    try {
      const response = await fetch(`${API}/loading-conditions`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : "Сервер отклонил данные. Проверьте поля и единицы.");
      }
      setNotice("Загрузочное условие сохранено как REVIEW_REQUIRED. Расчёты не выполнялись.");
      const refreshed = await fetch(`${API}/vessels/${encodeURIComponent(vesselId)}/loading-conditions`);
      if (refreshed.ok) setRecords(await refreshed.json() as LoadingSummary[]);
      formElement.reset();
      setItemRows([0]);
      setNextItemRow(1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось сохранить запись.");
    } finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><div><div className="eyebrow">ИСХОДНЫЕ ДАННЫЕ ЗАГРУЗКИ</div><h1>Загрузочные условия</h1><p>Сохранение масс и исходных положений. Эта форма не выполняет расчёт водоизмещения или остойчивости.</p></div></div>
    <div className="notice"><span className="notice-icon">!</span><div><strong>Только черновой ввод</strong><p>В этой версии доступны твёрдые нагрузки с заданными координатами. Танки, жидкие нагрузки, плотности и свободные поверхности ещё не реализованы.</p></div></div>
    {apiState !== "online" && <div className="inline-alert error">Нет подключения к локальному API. Запустите backend и примените миграции Alembic.</div>}
    {error && <div className="inline-alert error">{error}</div>}{notice && <div className="inline-alert success">{notice}</div>}
    <section className="panel vessel-form-panel">
      <div className="panel-heading"><div><div className="eyebrow">НОВАЯ ЗАПИСЬ</div><h2>Создать загрузочное условие</h2></div></div>
      {vessels.length === 0 ? <div className="empty-state"><strong>Сначала зарегистрируйте судно</strong><p>Загрузочное условие должно быть связано с конкретным профилем судна.</p></div> : <form onSubmit={submit}>
        <div className="form-grid">
          <label>Судно<select required value={vesselId} onChange={event => setVesselId(event.target.value)}><option value="">Выберите судно</option>{vessels.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</select></label>
          <label>Название условия<input name="condition_name" required maxLength={120} placeholder="Например, Перед выходом из порта" /></label>
          <label>Версия исходных данных судна<input name="revision" required maxLength={80} placeholder="Идентификатор ревизии / черновика" /></label>
          {itemRows.map((index, rowNumber) => <div className="load-item-editor" key={index}>
            <div className="form-subheading">Нагрузка {rowNumber + 1}</div>
            <div className="form-grid">
              <label>Идентификатор<input name={`item_id_${index}`} required maxLength={80} placeholder="Например, cargo-001" /></label>
              <label>Описание<input name={`description_${index}`} required maxLength={240} placeholder="Описание по грузовому плану" /></label>
              <label>Тип нагрузки<select name={`kind_${index}`} defaultValue="cargo"><option value="cargo">Груз</option><option value="stores">Судовые запасы</option><option value="crew_and_effects">Экипаж и багаж</option><option value="other">Другое</option></select></label>
              <label>Масса, кг<input name={`mass_kg_${index}`} type="number" min="0.001" step="0.001" required /></label>
              <label>Координата X, м<input name={`x_m_${index}`} type="number" step="0.001" required /></label>
              <label>Координата Y, м<input name={`y_m_${index}`} type="number" step="0.001" required /></label>
              <label>Координата Z, м<input name={`z_m_${index}`} type="number" step="0.001" required /></label>
              <label>Источник координат<input name={`position_source_${index}`} required minLength={3} maxLength={500} placeholder="План размещения, шпангоут / отметка" /></label>
              <label>Источник массы<input name={`source_reference_${index}`} required minLength={3} maxLength={500} placeholder="Грузовой манифест, накладная, ведомость" /></label>
            </div>
            {itemRows.length > 1 && <div className="form-actions"><button type="button" className="secondary-button" onClick={() => setItemRows(rows => rows.filter(row => row !== index))}>Удалить эту нагрузку</button></div>}
          </div>)}
          <div className="form-actions"><button type="button" className="secondary-button" onClick={() => { setItemRows(rows => [...rows, nextItemRow]); setNextItemRow(value => value + 1); }}>＋ Добавить нагрузку</button></div>
        </div>
        <label className="notes-label">Примечание<textarea name="notes" maxLength={2000} rows={2} placeholder="Необязательное примечание" /></label>
        <div className="form-actions"><button className="primary-button" type="submit" disabled={busy || apiState !== "online" || !vesselId}>{busy ? "Сохранение…" : "Сохранить черновик"}</button></div>
      </form>}
    </section>
    <section className="panel vessel-list"><div className="panel-heading"><div><div className="eyebrow">ИСТОРИЯ</div><h2>Сохранённые условия</h2></div></div>
      {!vesselId ? <div className="empty-state"><p>Выберите судно, чтобы просмотреть его загрузочные условия.</p></div> : records.length === 0 ? <div className="empty-state"><strong>Записей пока нет</strong><p>Создайте первое черновое загрузочное условие.</p></div> :
      <div className="vessel-table-wrap"><table className="vessel-table"><thead><tr><th>Название</th><th>Версия данных</th><th>Строк нагрузки</th><th>Статус</th></tr></thead><tbody>{records.map(record => <tr key={record.id}><td><strong>{record.name}</strong><small>{record.id}</small></td><td>{record.vessel_data_revision}</td><td>{record.item_count}</td><td><span className="draft-tag">{record.status}</span></td></tr>)}</tbody></table></div>}
    </section>
  </>;
}

function AxisSelect({ name, label, options }: { name: string; label: string; options: [string,string][] }) {
  return <label>{label}<select name={name} required defaultValue=""><option value="" disabled>Выберите по документации</option>{options.map(([value,text]) => <option key={value} value={value}>{text}</option>)}</select></label>;
}
function Metric({ label, value, detail }: { label: string; value: string; detail: string }) { return <div className="metric-card"><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>; }
function SetupStep({ number, title, description }: { number: string; title: string; description: string }) { return <div className="setup-step"><span className="step-number">{number}</span><div><strong>{title}</strong><p>{description}</p></div><span className="step-arrow">→</span></div>; }
function StatusRow({ name, status }: { name: string; status: string }) { return <div className="status-row"><span className="status-dot" /><span>{name}</span><small>{status}</small></div>; }
export default App;
