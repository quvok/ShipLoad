import { useCallback, useEffect, useState, type FormEvent } from "react";

type NavKey = "overview" | "vessels" | "tanks" | "documents" | "loading" | "reports";
type VesselType = "general_cargo" | "container" | "bulk_carrier" | "tanker" | "multipurpose" | "other";
type Vessel = {
  id: string; name: string; vessel_type: VesselType; loa_m: number | null; lbp_m: number | null;
  moulded_breadth_m: number | null; moulded_depth_m: number | null; data_status: string; created_at: string;
};
const navigation: { key: NavKey; label: string; icon: string }[] = [
  { key: "overview", label: "Обзор", icon: "◫" }, { key: "vessels", label: "Суда", icon: "▤" },
  { key: "tanks", label: "Танки", icon: "▥" },
  { key: "documents", label: "Документы", icon: "▧" }, { key: "loading", label: "Загрузочные условия", icon: "⌁" },
  { key: "reports", label: "Расчёты", icon: "▥" },
];
const vesselTypes: { value: VesselType; label: string }[] = [
  { value: "general_cargo", label: "Генеральный груз" }, { value: "container", label: "Контейнеровоз" },
  { value: "bulk_carrier", label: "Балкер" }, { value: "tanker", label: "Танкер" },
  { value: "multipurpose", label: "Многоцелевое судно" }, { value: "other", label: "Другое" },
];
const API = window.location.hostname === "quvok.github.io"
  ? "http://127.0.0.1:8000/api/v1"
  : "/api/v1";

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
      await loadVessels(); setShowForm(false); setActive("documents"); setSuccess("Черновик создан. Теперь загрузите судовую документацию.");
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
          {active === "documents" ? (<DocumentsPage vessels={vessels} apiState={apiState} />) : active === "loading" ? (<LoadingPage vessels={vessels} apiState={apiState} />) : active === "tanks" ? (
            <TanksPage vessels={vessels} apiState={apiState} />
          ) : active === "vessels" ? (
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
        <p className="form-hint">Сначала создаётся пустой черновик. Размерения и система координат будут извлечены из загруженных судовых документов и появятся для проверки с указанием страниц и источников. Не вводите их вручную, если они есть в документации.</p>
        <div className="form-grid">
          <label>Название судна<input name="name" required maxLength={120} placeholder="Можно указать временное название" /></label>
          <label>Тип судна<select name="vessel_type" required defaultValue="other">{vesselTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select></label>
        </div>
        <div className="form-actions"><button type="button" className="secondary-button" onClick={() => setShowForm(false)}>Отмена</button><button className="primary-button" type="submit" disabled={loading || apiState !== "online"}>{loading ? "Создание…" : "Создать пустой черновик"}</button></div>
      </form>
    </section>}
    <section className="panel vessel-list"><div className="panel-heading"><div><div className="eyebrow">ЛОКАЛЬНАЯ БАЗА ДАННЫХ</div><h2>Зарегистрированные суда</h2></div><button className="secondary-button" onClick={onRefresh}>Обновить</button></div>
      {vessels.length === 0 ? <div className="empty-state"><div className="empty-icon">▤</div><strong>Список судов пуст</strong><p>Создайте первый профиль. Запись будет сохранена в локальной SQLite-базе backend.</p></div> :
        <div className="vessel-table-wrap"><table className="vessel-table"><thead><tr><th>Название</th><th>Тип</th><th>LOA × B, м</th><th>LBP, м</th><th>Статус данных</th></tr></thead><tbody>{vessels.map((vessel) => <tr key={vessel.id}><td><strong>{vessel.name}</strong><small>{vessel.id}</small></td><td>{vesselTypes.find((type) => type.value === vessel.vessel_type)?.label ?? vessel.vessel_type}</td><td>{vessel.loa_m ?? "—"} × {vessel.moulded_breadth_m ?? "—"}</td><td>{vessel.lbp_m ?? "—"}</td><td><span className="draft-tag">{vessel.data_status}</span></td></tr>)}</tbody></table></div>}
    </section>
  </>;
}


type SourceDocument = {
  id: string; vessel_id: string; original_filename: string; media_type: string;
  size_bytes: number; sha256: string; document_type: string;
  extraction_status: string; candidate_count: number; uploaded_at: string;
};
type ExtractionReport = {
  page_count: number;
  pages_with_text: number;
  pages_without_text: number[];
  sections: Record<string, {
    label: string; status: string; evidence_count: number;
    evidence: { page: number; matched_terms: string[]; excerpt: string }[];
    note: string;
  }>;
  limitations: string[];
  dataset_coverage?: {
    coverage_version: number;
    status: string;
    datasets: {
      key: string; label: string; status: string; evidence_pages: number[];
      text_evidence_count: number; table_evidence_count: number;
      review_required: boolean; note: string;
    }[];
    limitations: string[];
  };
  table_analysis?: {
    status: string; candidate_pages: number[]; pages_checked: number[];
    pages_skipped_by_limit: number[]; pages_skipped_complex: number[]; tables_found: number;
    tables: { page: number; kind: string; label: string; row_count_preview: number;
      column_count_preview: number; rows: string[][]; note: string }[];
    page_errors: { page: number | null; error: string }[]; note: string;
  };
};

type ExtractedCandidate = {
  field: string; value: number; unit: string; page: number; matched_text: string; status: string;
  evidence?: { page: number; matched_text: string }[];
  candidate_index: number; candidate_indices?: number[]; review_status: string;
  decision: { reviewer_label: string; decided_at: string; comment: string | null; approved_value: number | null; revision_number: number | null; revision_numbers?: number[] } | null;
};
const documentTypes = [
  ["ship_particulars", "Основные характеристики судна"],
  ["stability_booklet", "Информация об остойчивости"],
  ["general_arrangement", "Общее расположение"],
  ["lines_plan", "Теоретический чертёж"],
  ["other", "Другой документ"],
];
const candidateLabels: Record<string, string> = {
  loa_m: "Длина наибольшая (LOA)",
  lbp_m: "Длина между перпендикулярами (LBP)",
  moulded_breadth_m: "Теоретическая ширина (B)",
  moulded_depth_m: "Теоретическая высота борта (D)",
};
function DocumentsPage({ vessels, apiState }: { vessels: Vessel[]; apiState: "checking" | "online" | "offline" }) {
  const [vesselId, setVesselId] = useState("");
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [candidates, setCandidates] = useState<ExtractedCandidate[]>([]);
  const [report, setReport] = useState<ExtractionReport | null>(null);
  const [selectedDocument, setSelectedDocument] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reviewerLabel, setReviewerLabel] = useState("");
  const [correctedValues, setCorrectedValues] = useState<Record<number, string>>({});
  const [reviewingCandidate, setReviewingCandidate] = useState<number | null>(null);
  const loadDocuments = useCallback(async (id: string) => {
    if (!id) { setDocuments([]); setCandidates([]); setSelectedDocument(""); return; }
    const response = await fetch(`${API}/vessels/${encodeURIComponent(id)}/documents`);
    if (!response.ok) throw new Error("Не удалось получить список документов.");
    setDocuments(await response.json() as SourceDocument[]);
  }, []);
  useEffect(() => {
    setError("");
    void loadDocuments(vesselId).catch(cause => setError(cause instanceof Error ? cause.message : "Ошибка загрузки документов."));
  }, [vesselId, loadDocuments]);
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!vesselId) return;
    setBusy(true); setError(""); setMessage("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      const response = await fetch(`${API}/vessels/${encodeURIComponent(vesselId)}/documents`, { method: "POST", body: form });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : "Не удалось загрузить документ.");
      }
      const created = await response.json() as SourceDocument;
      await loadDocuments(vesselId);
      setSelectedDocument(created.id);
      setMessage("Оригинал сохранён. Извлечённые значения доступны для сверки; автоматически они не утверждаются.");
      formElement.reset();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка загрузки документа.");
    } finally { setBusy(false); }
  }
  useEffect(() => {
    if (!selectedDocument) { setCandidates([]); return; }
    void fetch(`${API}/documents/${encodeURIComponent(selectedDocument)}/candidates`)
      .then(async response => {
        if (!response.ok) throw new Error("Не удалось получить результаты извлечения.");
        return await response.json() as { candidates: ExtractedCandidate[] };
      })
      .then(data => setCandidates(data.candidates))
      .catch(cause => setError(cause instanceof Error ? cause.message : "Ошибка получения кандидатов."));
  }, [selectedDocument]);
  useEffect(() => {
    setReport(null);
    if (!selectedDocument) return;
    void fetch(`${API}/documents/${encodeURIComponent(selectedDocument)}/report`)
      .then(async response => {
        if (!response.ok) throw new Error("Не удалось получить полный отчёт анализа документа.");
        return await response.json() as { report: ExtractionReport };
      })
      .then(data => setReport(data.report))
      .catch(cause => setError(cause instanceof Error ? cause.message : "Ошибка анализа документа."));
  }, [selectedDocument]);
  async function reviewCandidate(item: ExtractedCandidate, decision: "APPROVE" | "REJECT") {
    if (reviewerLabel.trim().length < 2) {
      setError("Укажите имя или должность проверяющего (не менее 2 символов).");
      return;
    }
    setReviewingCandidate(item.candidate_index); setError(""); setMessage("");
    const payload: { decision: string; reviewer_label: string; approved_value?: number } = {
      decision,
      reviewer_label: reviewerLabel.trim(),
    };
    if (decision === "APPROVE") {
      const value = Number(correctedValues[item.candidate_index] ?? item.value);
      if (!Number.isFinite(value) || value <= 0) {
        setError("Укажите корректное положительное значение в метрах.");
        setReviewingCandidate(null);
        return;
      }
      payload.approved_value = value;
    }
    try {
      const response = await fetch(`${API}/documents/${encodeURIComponent(selectedDocument)}/candidates/${item.candidate_index}/decision`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "Не удалось сохранить решение.");
      const refreshed = await fetch(`${API}/documents/${encodeURIComponent(selectedDocument)}/candidates`);
      if (!refreshed.ok) throw new Error("Решение сохранено, но не удалось обновить список кандидатов.");
      const data = await refreshed.json() as { candidates: ExtractedCandidate[] };
      setCandidates(data.candidates);
      setMessage(body.message);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка при проверке кандидата.");
    } finally { setReviewingCandidate(null); }
  }
  async function approveAllCandidates() {
    const pending = candidates.filter(item => item.review_status === "PENDING");
    if (!pending.length) return;
    if (reviewerLabel.trim().length < 2) {
      setError("Укажите имя или должность проверяющего (не менее 2 символов).");
      return;
    }
    const items = pending.map(item => ({
      candidate_index: item.candidate_index,
      approved_value: Number(correctedValues[item.candidate_index] ?? item.value),
    }));
    if (items.some(item => !Number.isFinite(item.approved_value) || item.approved_value <= 0)) {
      setError("Проверьте все значения перед пакетным подтверждением.");
      return;
    }
    setReviewingCandidate(-1); setError(""); setMessage("");
    try {
      const response = await fetch(`${API}/documents/${encodeURIComponent(selectedDocument)}/candidates/approve-batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewer_label: reviewerLabel.trim(), items }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "Не удалось пакетно подтвердить кандидаты.");
      const refreshed = await fetch(`${API}/documents/${encodeURIComponent(selectedDocument)}/candidates`);
      if (!refreshed.ok) throw new Error("Ревизия сохранена, но список кандидатов не обновился.");
      const data = await refreshed.json() as { candidates: ExtractedCandidate[] };
      setCandidates(data.candidates);
      setMessage(body.message);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка пакетного подтверждения.");
    } finally { setReviewingCandidate(null); }
  }
  const selected = documents.find(doc => doc.id === selectedDocument);
  return <>
    <div className="page-heading"><div><div className="eyebrow">ИСТОЧНИКИ ДАННЫХ СУДНА</div><h1>Документы</h1><p>Загрузите один PDF. Система анализирует весь документ и формирует обзор найденных разделов и значений с привязкой к страницам.</p></div></div>
    <div className="notice"><span className="notice-icon">!</span><div><strong>Распознавание не означает подтверждение</strong><p>Файлы хранятся в локальной папке backend вне публичной директории. Кандидаты необходимо сверить с оригиналом. Сканированные документы пока требуют отдельного OCR-модуля.</p></div></div>
    {apiState !== "online" && <div className="inline-alert error">Для работы с документами необходимо подключение к локальному API.</div>}
    {error && <div className="inline-alert error">{error}</div>}{message && <div className="inline-alert success">{message}</div>}
    <section className="panel vessel-form-panel">
      <div className="panel-heading"><div><div className="eyebrow">ЗАГРУЗКА ИСТОЧНИКА</div><h2>Добавить судовой документ</h2></div></div>
      <form onSubmit={upload}>
        <div className="form-grid">
          <label>Судно<select value={vesselId} onChange={event => setVesselId(event.target.value)} required><option value="">Выберите судно</option>{vessels.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</select></label>
          <input type="hidden" name="document_type" value="other" /><div className="form-hint">Тип и состав документа определяются автоматически по его содержимому.</div>
          <label>Файл PDF<input name="file" type="file" accept="application/pdf,.pdf" required /></label>
        </div>
        <div className="form-actions"><button className="primary-button" type="submit" disabled={busy || apiState !== "online" || !vesselId}>{busy ? "Загрузка…" : "Загрузить и извлечь данные"}</button></div>
      </form>
    </section>
    <section className="panel vessel-list">
      <div className="panel-heading"><div><div className="eyebrow">АРХИВ ОРИГИНАЛОВ</div><h2>Загруженные документы</h2></div><button className="secondary-button" onClick={() => void loadDocuments(vesselId)} disabled={!vesselId}>Обновить</button></div>
      {!vesselId ? <div className="empty-state">Сначала выберите судно.</div> : documents.length === 0 ? <div className="empty-state">Для выбранного судна документы ещё не загружены.</div> :
        <div className="vessel-table-wrap"><table className="vessel-table"><thead><tr><th>Файл</th><th>Тип</th><th>Объём</th><th>Извлечение</th><th>Кандидаты</th></tr></thead><tbody>{documents.map(doc => <tr key={doc.id} onClick={() => setSelectedDocument(doc.id)} className={selectedDocument === doc.id ? "selected-row" : ""}><td><strong>{doc.original_filename}</strong><small>SHA-256: {doc.sha256.slice(0,16)}…</small></td><td>{documentTypes.find(([value]) => value === doc.document_type)?.[1] ?? doc.document_type}</td><td>{(doc.size_bytes / 1024).toFixed(1)} КБ</td><td>{doc.extraction_status}</td><td>{doc.candidate_count}</td></tr>)}</tbody></table></div>}
    </section>
    {selected && <section className="panel vessel-list"><div className="panel-heading"><div><div className="eyebrow">РЕЗУЛЬТАТ ИЗВЛЕЧЕНИЯ</div><h2>{selected.original_filename}</h2><a className="help-button" href={`${API}/documents/${encodeURIComponent(selected.id)}/file`} target="_blank" rel="noreferrer">Открыть оригинал ↗</a></div><span className="draft-tag">ТРЕБУЕТ СВЕРКИ</span></div>
      {report && <div className="extraction-report">
        <div className="eyebrow">ПОЛНЫЙ ОБЗОР ДОКУМЕНТА</div>
        <p>Проанализировано страниц: <strong>{report.page_count}</strong>; с текстовым слоем: <strong>{report.pages_with_text}</strong>; без извлечённого текста: <strong>{report.pages_without_text.length}</strong>.</p>
        {report.dataset_coverage && <section className="table-analysis">
          <div className="report-section-heading"><strong>Покрытие наборов данных судна</strong><span className="draft-tag">Требует проверки</span></div>
          <p>Сводка объединяет текстовые указатели и классифицированные табличные фрагменты. Наличие источника не означает, что таблица полностью распознана или подтверждена.</p>
          <div className="report-section-grid">{report.dataset_coverage.datasets.map(dataset =>
            <article className="report-section" key={dataset.key}>
              <div className="report-section-heading"><strong>{dataset.label}</strong><span className="draft-tag">
                {dataset.status === "TABLE_EVIDENCE_REVIEW_REQUIRED" ? "Есть таблица" :
                  dataset.status === "TEXT_EVIDENCE_REVIEW_REQUIRED" ? "Есть текст" :
                  dataset.status === "EXTRACTION_INCOMPLETE" ? "Извлечение неполное" : "Нет совпадений"}
              </span></div>
              <p>{dataset.note}</p>
              <p className="form-hint">Страницы: {dataset.evidence_pages.length ? dataset.evidence_pages.join(", ") : "не определены"} · текстовых указателей: {dataset.text_evidence_count} · таблиц: {dataset.table_evidence_count}</p>
            </article>
          )}</div>
          <div className="form-hint"><strong>Ограничения покрытия:</strong><ul>{report.dataset_coverage.limitations.map(item => <li key={item}>{item}</li>)}</ul></div>
        </section>}
        <div className="report-section-grid">{Object.entries(report.sections).map(([key, section]) =>
          <article className="report-section" key={key}>
            <div className="report-section-heading"><strong>{section.label}</strong><span className="draft-tag">{section.status === "TEXT_EVIDENCE_FOUND" ? "Есть совпадения" : section.status === "OCR_REQUIRED" ? "Требуется OCR" : "Не найдено в тексте"}</span></div>
            <p>{section.note}</p>
            {section.evidence.length > 0 && <ul>{section.evidence.slice(0, 5).map((item, index) =>
              <li key={index}><strong>Стр. {item.page}:</strong> {item.excerpt}</li>
            )}</ul>}
          </article>
        )}</div>
        {report.table_analysis && <section className="table-analysis">
          <div className="report-section-heading"><strong>Структурное извлечение таблиц</strong><span className="draft-tag">{report.table_analysis.tables_found} таблиц</span></div>
          <p>{report.table_analysis.note}</p>
          <p className="form-hint">Проверены страницы: {report.table_analysis.pages_checked.length ? report.table_analysis.pages_checked.join(", ") : "нет"}.
            {report.table_analysis.pages_skipped_by_limit.length > 0 ? ` Пропущены по лимиту страниц: ${report.table_analysis.pages_skipped_by_limit.join(", ")}.` : ""}
            {report.table_analysis.pages_skipped_complex?.length > 0 ? ` Сложные векторные страницы пропущены ради ограничения нагрузки: ${report.table_analysis.pages_skipped_complex.join(", ")}.` : ""}
          </p>
          {report.table_analysis.tables.map((table, index) => <article className="report-section" key={`${table.page}-${index}`}>
            <div className="report-section-heading"><strong>{table.label}</strong><span className="draft-tag">Стр. {table.page}</span></div>
            <div className="vessel-table-wrap"><table className="vessel-table"><tbody>
              {table.rows.slice(0, 12).map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell || "—"}</td>)}</tr>)}
            </tbody></table></div>
            <p className="form-hint">{table.note}</p>
          </article>)}
        </section>}
        <div className="form-hint"><strong>Ограничения анализа:</strong><ul>{report.limitations.map(item => <li key={item}>{item}</li>)}</ul></div>
      </div>}
      {candidates.length === 0 ? <div className="empty-state">{selected.extraction_status === "OCR_REQUIRED" ? "В документе не найден текстовый слой. Для него потребуется OCR." : "Кандидаты характеристик не обнаружены. Проверьте документ вручную."}</div> : <>
        <label className="reviewer-label">Проверяющий (имя или должность)<input value={reviewerLabel} onChange={event => setReviewerLabel(event.target.value)} maxLength={80} placeholder="Например, старший помощник" /></label>
        <div className="form-actions"><button className="primary-button" type="button" disabled={reviewingCandidate !== null || !candidates.some(item => item.review_status === "PENDING")} onClick={() => void approveAllCandidates()}>Подтвердить все ожидающие одной ревизией</button><span className="form-hint">Перед нажатием сверьте каждое значение и все указанные страницы с оригиналом.</span></div>
        <div className="vessel-table-wrap"><table className="vessel-table"><thead><tr><th>Параметр</th><th>Кандидат / подтверждено, м</th><th>Страницы</th><th>Фрагменты источника</th><th>Решение</th></tr></thead><tbody>{candidates.map(item => <tr key={item.candidate_index}>
          <td>{candidateLabels[item.field] ?? item.field}</td>
          <td>{item.review_status === "PENDING" ? <input className="candidate-value" type="number" min="0.001" step="0.001" value={correctedValues[item.candidate_index] ?? String(item.value)} onChange={event => setCorrectedValues(current => ({ ...current, [item.candidate_index]: event.target.value }))} /> : <strong>{(item.decision?.approved_value ?? item.value).toFixed(3)}</strong>}</td>
          <td>{(item.evidence?.length ? item.evidence : [{ page: item.page, matched_text: item.matched_text }]).map(source => source.page).filter((page, index, pages) => pages.indexOf(page) === index).join(", ")}</td>
          <td>{(item.evidence?.length ? item.evidence : [{ page: item.page, matched_text: item.matched_text }]).map((source, index) => <div key={String(source.page) + "-" + index}><small>Стр. {source.page}:</small> {source.matched_text}</div>)}</td>
          <td>{item.review_status === "PENDING" ? <div className="candidate-actions">
            <button className="secondary-button" disabled={reviewingCandidate !== null} onClick={() => void reviewCandidate(item, "APPROVE")}>{reviewingCandidate === item.candidate_index ? "Сохранение…" : "Подтвердить"}</button>
            <button className="candidate-reject" disabled={reviewingCandidate !== null} onClick={() => void reviewCandidate(item, "REJECT")}>Отклонить</button>
          </div> : <span className={item.review_status === "APPROVE" ? "review-approved" : "review-rejected"}>{item.review_status === "APPROVE" ? "Подтверждено" : "Отклонено"}{item.decision?.revision_numbers?.length ? ` · ревизии ${item.decision.revision_numbers.join(", ")}` : item.decision?.revision_number ? ` · ревизия ${item.decision.revision_number}` : ""}<small>{item.decision?.reviewer_label}</small></span>}</td>
        </tr>)}</tbody></table></div>
      </>}
      <p className="form-hint">Подтверждение создаёт новую неизменяемую ревизию исходных данных с привязкой к PDF, странице, фрагменту, исходному и проверенному значению. Профиль судна не перезаписывается. Метка проверяющего пока не является аутентификацией: вход и персональные учётные записи ещё не реализованы. Решения не включают координатную систему и не разрешают эксплуатационные расчёты.</p>
    </section>}
  </>;
}

type TankType = "ballast" | "fuel_oil" | "diesel_oil" | "fresh_water" | "lubricating_oil" | "sewage" | "sludge" | "other";
type Tank = {
  id: string; vessel_id: string; tank_code: string; name: string; tank_type: TankType;
  nominal_capacity_m3: number | null; arrangement_source_reference: string;
  capacity_source_reference: string | null; data_status: string;
};
const tankTypes: { value: TankType; label: string }[] = [
  { value: "ballast", label: "Балластный" }, { value: "fuel_oil", label: "Топливный" },
  { value: "diesel_oil", label: "Дизельное топливо" }, { value: "fresh_water", label: "Пресная вода" },
  { value: "lubricating_oil", label: "Смазочное масло" }, { value: "sewage", label: "Сточные воды" },
  { value: "sludge", label: "Шлам" }, { value: "other", label: "Другой" },
];
function TanksPage({ vessels, apiState }: { vessels: Vessel[]; apiState: "checking" | "online" | "offline" }) {
  const [vesselId, setVesselId] = useState("");
  const [tanks, setTanks] = useState<Tank[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const loadTanks = useCallback(async (id: string) => {
    if (!id) { setTanks([]); return; }
    const response = await fetch(`${API}/vessels/${encodeURIComponent(id)}/tanks`);
    if (!response.ok) throw new Error("Не удалось получить реестр танков.");
    setTanks(await response.json() as Tank[]);
  }, []);
  useEffect(() => {
    setError("");
    void loadTanks(vesselId).catch(cause => setError(cause instanceof Error ? cause.message : "Ошибка загрузки реестра."));
  }, [vesselId, loadTanks]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const capacityText = String(form.get("nominal_capacity_m3") ?? "").trim();
    const payload = {
      tank_code: String(form.get("tank_code") ?? "").trim(),
      name: String(form.get("name") ?? "").trim(),
      tank_type: form.get("tank_type"),
      nominal_capacity_m3: capacityText ? Number(capacityText) : null,
      arrangement_source_reference: String(form.get("arrangement_source_reference") ?? "").trim(),
      capacity_source_reference: String(form.get("capacity_source_reference") ?? "").trim() || null,
    };
    try {
      const response = await fetch(`${API}/vessels/${encodeURIComponent(vesselId)}/tanks`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = body?.detail;
        throw new Error(typeof detail === "string" ? detail : "Сервер отклонил данные. Проверьте вместимость и ссылки на документы.");
      }
      await loadTanks(vesselId);
      formElement.reset();
      setNotice("Танк зарегистрирован со статусом REVIEW_REQUIRED. Калибровочные таблицы ещё не загружены.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось сохранить танк.");
    } finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><div><div className="eyebrow">ТЕХНИЧЕСКИЕ ДАННЫЕ СУДНА</div><h1>Реестр танков</h1><p>Идентификация танков и регистрация подтверждённых документами исходных сведений.</p></div></div>
    <div className="notice"><span className="notice-icon">!</span><div><strong>Реестр — ещё не калибровочная модель</strong><p>Номинальная вместимость не позволяет определить фактический объём, массу, центр тяжести или поправку на свободную поверхность. Для этого потребуются проверенные таблицы замеров конкретного танка.</p></div></div>
    {apiState !== "online" && <div className="inline-alert error">Нет подключения к локальному API.</div>}
    {error && <div className="inline-alert error">{error}</div>}{notice && <div className="inline-alert success">{notice}</div>}
    <section className="panel vessel-form-panel">
      <div className="panel-heading"><div><div className="eyebrow">НОВАЯ ЗАПИСЬ</div><h2>Зарегистрировать танк</h2></div></div>
      {vessels.length === 0 ? <div className="empty-state"><strong>Сначала зарегистрируйте судно</strong><p>Танк должен принадлежать конкретному судну.</p></div> : <form onSubmit={submit}>
        <div className="form-grid">
          <label>Судно<select required value={vesselId} onChange={event => setVesselId(event.target.value)}><option value="">Выберите судно</option>{vessels.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</select></label>
          <label>Идентификатор танка<input name="tank_code" required maxLength={80} placeholder="Как в плане расположения танков" /></label>
          <label>Название<input name="name" required maxLength={120} placeholder="Название по судовой документации" /></label>
          <label>Тип танка<select name="tank_type" required defaultValue="ballast">{tankTypes.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}</select></label>
          <label>Номинальная вместимость, м³<input name="nominal_capacity_m3" type="number" min="0.001" step="0.001" placeholder="Необязательно" /></label>
          <label>Источник вместимости<input name="capacity_source_reference" maxLength={500} placeholder="Таблица вместимости, лист / страница" /></label>
          <label>Источник идентификации<input name="arrangement_source_reference" required minLength={3} maxLength={500} placeholder="План расположения танков, лист / страница" /></label>
        </div>
        <div className="form-actions"><button className="primary-button" type="submit" disabled={busy || apiState !== "online" || !vesselId}>{busy ? "Сохранение…" : "Сохранить танк"}</button></div>
      </form>}
    </section>
    <section className="panel vessel-list"><div className="panel-heading"><div><div className="eyebrow">ЛОКАЛЬНАЯ БАЗА ДАННЫХ</div><h2>Танки выбранного судна</h2></div><button className="secondary-button" onClick={() => void loadTanks(vesselId).catch(cause => setError(cause instanceof Error ? cause.message : "Ошибка загрузки."))} disabled={!vesselId}>Обновить</button></div>
      {!vesselId ? <div className="empty-state"><p>Выберите судно, чтобы просмотреть его танки.</p></div> : tanks.length === 0 ? <div className="empty-state"><strong>Танки ещё не зарегистрированы</strong><p>Добавьте их по плану расположения танков.</p></div> :
      <div className="vessel-table-wrap"><table className="vessel-table"><thead><tr><th>Идентификатор / название</th><th>Тип</th><th>Вместимость, м³</th><th>Источник вместимости</th><th>Статус</th></tr></thead><tbody>{tanks.map(t => <tr key={t.id}><td><strong>{t.tank_code}</strong><small>{t.name}</small></td><td>{tankTypes.find(x => x.value === t.tank_type)?.label ?? t.tank_type}</td><td>{t.nominal_capacity_m3 ?? "Не указана"}</td><td>{t.capacity_source_reference ?? "—"}</td><td><span className="draft-tag">{t.data_status}</span></td></tr>)}</tbody></table></div>}
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
  const [itemKinds, setItemKinds] = useState<Record<number, string>>({ 0: "cargo" });
  const [tankOptions, setTankOptions] = useState<Tank[]>([]);
  const liquidKinds = new Set(["ballast", "fuel_oil", "diesel_oil", "fresh_water", "lubricating_oil"]);
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

  useEffect(() => {
    if (!vesselId) { setTankOptions([]); return; }
    let cancelled = false;
    fetch(`${API}/vessels/${encodeURIComponent(vesselId)}/tanks`)
      .then(async response => {
        if (!response.ok) throw new Error("Не удалось получить реестр танков.");
        return await response.json() as Tank[];
      })
      .then(data => { if (!cancelled) setTankOptions(data); })
      .catch(() => { if (!cancelled) setTankOptions([]); });
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
      items: itemRows.map(index => {
        const kind = String(form.get(`kind_${index}`) ?? "cargo");
        const isLiquid = liquidKinds.has(kind);
        return {
          item_id: String(form.get(`item_id_${index}`) ?? "").trim(),
          description: String(form.get(`description_${index}`) ?? "").trim(),
          kind,
          mass_kg: Number(form.get(`mass_kg_${index}`)),
          position: isLiquid ? null : {
            x_m: Number(form.get(`x_m_${index}`)),
            y_m: Number(form.get(`y_m_${index}`)),
            z_m: Number(form.get(`z_m_${index}`)),
            position_source: String(form.get(`position_source_${index}`) ?? "").trim(),
          },
          tank_id: isLiquid ? String(form.get(`tank_id_${index}`) ?? "") : null,
          source_reference: String(form.get(`source_reference_${index}`) ?? "").trim(),
        };
      }),
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
      setItemKinds({ 0: "cargo" });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось сохранить запись.");
    } finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><div><div className="eyebrow">ИСХОДНЫЕ ДАННЫЕ ЗАГРУЗКИ</div><h1>Загрузочные условия</h1><p>Сохранение масс и исходных положений. Эта форма не выполняет расчёт водоизмещения или остойчивости.</p></div></div>
    <div className="notice"><span className="notice-icon">!</span><div><strong>Только черновой ввод</strong><p>Для жидких нагрузок можно выбрать зарегистрированный танк и вручную указать массу со ссылкой на проверенный источник замера/расчёта. Преобразование уровня в объём и массу, плотность и поправка на свободную поверхность пока не реализованы.</p></div></div>
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
              <label>Тип нагрузки<select name={`kind_${index}`} value={itemKinds[index] ?? "cargo"} onChange={event => setItemKinds(current => ({ ...current, [index]: event.target.value }))}>
                <option value="cargo">Груз</option><option value="ballast">Балласт</option><option value="fuel_oil">Топливо</option><option value="diesel_oil">Дизельное топливо</option><option value="fresh_water">Пресная вода</option><option value="lubricating_oil">Смазочное масло</option><option value="stores">Судовые запасы</option><option value="crew_and_effects">Экипаж и багаж</option><option value="other">Другое</option></select></label>
              <label>Масса, кг<input name={`mass_kg_${index}`} type="number" min="0.001" step="0.001" required /></label>
              {liquidKinds.has(itemKinds[index] ?? "cargo") ? <>
                <label>Танк<select name={`tank_id_${index}`} required defaultValue=""><option value="">Выберите зарегистрированный танк</option>{tankOptions.filter(t => t.tank_type === itemKinds[index]).map(t => <option key={t.id} value={t.id}>{t.tank_code} — {t.name}</option>)}</select></label>
                <p className="form-hint">Массу укажите по проверенному источнику. Приложение пока не пересчитывает замер в объём или массу.</p>
              </> : <>
                <label>Координата X, м<input name={`x_m_${index}`} type="number" step="0.001" required /></label>
                <label>Координата Y, м<input name={`y_m_${index}`} type="number" step="0.001" required /></label>
                <label>Координата Z, м<input name={`z_m_${index}`} type="number" step="0.001" required /></label>
                <label>Источник координат<input name={`position_source_${index}`} required minLength={3} maxLength={500} placeholder="План размещения, шпангоут / отметка" /></label>
              </>}
              <label>Источник массы<input name={`source_reference_${index}`} required minLength={3} maxLength={500} placeholder="Манифест, ведомость, проверенный расчёт" /></label>
            </div>
            {itemRows.length > 1 && <div className="form-actions"><button type="button" className="secondary-button" onClick={() => setItemRows(rows => rows.filter(row => row !== index))}>Удалить эту нагрузку</button></div>}
          </div>)}
          <div className="form-actions"><button type="button" className="secondary-button" onClick={() => { setItemRows(rows => [...rows, nextItemRow]); setItemKinds(current => ({ ...current, [nextItemRow]: "cargo" })); setNextItemRow(value => value + 1); }}>＋ Добавить нагрузку</button></div>
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
