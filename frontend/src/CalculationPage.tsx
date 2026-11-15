import { useEffect, useState, type FormEvent } from "react";

type VesselOption = { id: string; name: string; lbp_m: number | null };
type WeightForm = {
  name: string; mass_t: string; lcg_m: string; tcg_m: string; vcg_m: string;
  free_surface_moment_tm: string; source_reference: string;
};
type HydroForm = {
  displacement_volume_m3: string; draft_extreme_m: string; lcf_from_ap_m: string;
  lcb_from_ap_m: string; transverse_metacentre_z_m: string; mct_t_m_per_cm: string;
  source_reference: string;
};
type KnForm = { heel_angle_deg: string; kn_m: string; source_reference: string };
type RunSummary = {
  id: string; name: string; status: string; created_at: string; displacement_t: number;
  mean_draft_m: number; engine_version: string;
};
type CalculationResult = {
  status: string; engine_version: string; warnings: string[];
  outputs: Record<string, number | null>;
  stability_curve: null | {
    points: { heel_angle_deg: number; kn_m: number; gz_m: number; dynamic_arm_m_rad: number }[];
    maximum_gz_m: number; heel_angle_at_maximum_deg: number;
    area_to_30_deg_m_rad: number | null; area_to_40_deg_m_rad: number | null;
    area_30_to_40_deg_m_rad: number | null; note: string;
  };
  interpolation: { method: string; extrapolation: string; table_volume_min_m3: number; table_volume_max_m3: number };
};
type RunDetails = {
  id: string; name: string; calculation_result: CalculationResult;
  calculation_input?: {
    coordinate_convention: string; lightship: { source_reference: string; strength_source_reference?: string | null };
    items: { name: string; source_reference: string }[];
    hydrostatic_table: { source_reference: string }[];
    kn_curve?: { source_reference: string }[];
  };
};
type LightshipForm = {
  mass_t: string; lcg_m: string; tcg_m: string; vcg_m: string; source_reference: string;
  forward_strength_moment_tm: string; strength_source_reference: string;
};

const blankWeight = (): WeightForm => ({ name: "", mass_t: "", lcg_m: "", tcg_m: "", vcg_m: "", free_surface_moment_tm: "0", source_reference: "" });
const blankHydro = (): HydroForm => ({ displacement_volume_m3: "", draft_extreme_m: "", lcf_from_ap_m: "", lcb_from_ap_m: "", transverse_metacentre_z_m: "", mct_t_m_per_cm: "", source_reference: "" });
const blankKn = (): KnForm => ({ heel_angle_deg: "", kn_m: "", source_reference: "" });
const blankLightship: LightshipForm = { mass_t: "", lcg_m: "", tcg_m: "", vcg_m: "", source_reference: "", forward_strength_moment_tm: "", strength_source_reference: "" };
const API = window.location.hostname === "quvok.github.io" ? "http://127.0.0.1:8000/api/v1" : "/api/v1";

function courseExample() {
  const course = "КП KP_TUS_Gr1_P18_3, таблица оптимального плана, стр. 17";
  return {
    name: "Учебный пример: оптимальный план по курсовому проекту",
    revision: "КП 2026 / Информация об остойчивости DA101Z035",
    lbp: "283.10", density: "1.018",
    coordinate: "Начало в AP на основной плоскости; X положительный в нос, Y на левый борт, Z вверх.",
    lightship: { mass_t: "47087.2", lcg_m: "119.245", tcg_m: "-0.106", vcg_m: "16.538", source_reference: "КП KP_TUS_Gr1_P18_3, таблица 1.3, стр. 6", forward_strength_moment_tm: "", strength_source_reference: "" },
    items: [
      { name: "Груз", mass_t: "84190.0", lcg_m: "154.03", tcg_m: "0.00", vcg_m: "16.77", free_surface_moment_tm: "103989.5", source_reference: course },
      { name: "Пресная вода", mass_t: "279.8", lcg_m: "17.16", tcg_m: "5.83", vcg_m: "23.32", free_surface_moment_tm: "778.6", source_reference: course },
      { name: "Дизельное топливо", mass_t: "220.0", lcg_m: "49.99", tcg_m: "20.36", vcg_m: "16.32", free_surface_moment_tm: "278.3", source_reference: course },
      { name: "Масло", mass_t: "395.4", lcg_m: "24.23", tcg_m: "-0.54", vcg_m: "19.62", free_surface_moment_tm: "248.6", source_reference: course },
      { name: "Тяжёлое топливо", mass_t: "4086.0", lcg_m: "202.93", tcg_m: "-0.09", vcg_m: "16.05", free_surface_moment_tm: "22669.7", source_reference: course },
      { name: "Отходы", mass_t: "247.0", lcg_m: "31.59", tcg_m: "20.01", vcg_m: "12.90", free_surface_moment_tm: "231.8", source_reference: course },
      { name: "Сторонние нагрузки", mass_t: "199.0", lcg_m: "110.02", tcg_m: "0.00", vcg_m: "28.38", free_surface_moment_tm: "20.0", source_reference: course },
      { name: "Балласт в ахтерпике", mass_t: "1100.0", lcg_m: "-9.20", tcg_m: "0.00", vcg_m: "16.09", free_surface_moment_tm: "13705.9", source_reference: course },
    ],
    hydro: [
      { displacement_volume_m3: "134919", draft_extreme_m: "12.650", lcf_from_ap_m: "129.61", lcb_from_ap_m: "141.39", transverse_metacentre_z_m: "25.44", mct_t_m_per_cm: "2780.6", source_reference: "Информация об остойчивости DA101Z035, PDF стр. 82, гидростатика, осадка 12.65 м" },
      { displacement_volume_m3: "135573", draft_extreme_m: "12.700", lcf_from_ap_m: "129.49", lcb_from_ap_m: "141.33", transverse_metacentre_z_m: "25.41", mct_t_m_per_cm: "2792.7", source_reference: "Информация об остойчивости DA101Z035, PDF стр. 82, гидростатика, осадка 12.70 м" },
    ],
    kn: [
      [0,"0.000"],[0.1,"0.045"],[5,"2.222"],[10,"4.429"],[15,"6.609"],
      [20,"8.785"],[30,"13.061"],[40,"15.975"],[50,"17.598"],[60,"18.421"],
    ].map(([angle,arm]) => ({ heel_angle_deg: String(angle), kn_m: String(arm), source_reference: "КП KP_TUS_Gr1_P18_3, таблица 6.1, плечи KN из Информации об остойчивости DA101Z035" })),
  };
}

function n(value: string) { return Number(value); }
function fmt(value: number | null | undefined, digits = 3) { return value == null ? "Не рассчитано" : value.toLocaleString("ru-RU", { minimumFractionDigits: digits, maximumFractionDigits: digits }); }
function responseError(body: unknown, fallback: string) {
  if (!body || typeof body !== "object" || !("detail" in body)) return fallback;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((entry) => {
      if (!entry || typeof entry !== "object") return String(entry);
      const issue = entry as { loc?: unknown[]; msg?: unknown };
      const path = issue.loc?.filter((part) => part !== "body").join(" → ");
      return `${path ? `${path}: ` : ""}${typeof issue.msg === "string" ? issue.msg : "ошибка проверки поля"}`;
    });
    return messages.length ? `Проверьте данные расчёта: ${messages.join("; ")}` : fallback;
  }
  return fallback;
}

export default function CalculationPage({ vessels, apiState }: { vessels: VesselOption[]; apiState: "checking" | "online" | "offline" }) {
  const [vesselId, setVesselId] = useState("");
  const [name, setName] = useState("");
  const [revision, setRevision] = useState("");
  const [coordinate, setCoordinate] = useState("");
  const [lbp, setLbp] = useState("");
  const [density, setDensity] = useState("1.025");
  const [lightship, setLightship] = useState<LightshipForm>(blankLightship);
  const [items, setItems] = useState<WeightForm[]>([blankWeight()]);
  const [hydro, setHydro] = useState<HydroForm[]>([blankHydro(), blankHydro()]);
  const [knCurve, setKnCurve] = useState<KnForm[]>([]);
  const [history, setHistory] = useState<RunSummary[]>([]);
  const [result, setResult] = useState<RunDetails | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!vesselId) { setHistory([]); return; }
    let cancelled = false;
    fetch(`${API}/vessels/${encodeURIComponent(vesselId)}/calculation-runs`)
      .then(async response => { if (!response.ok) throw new Error("Не удалось получить историю расчётов."); return await response.json() as RunSummary[]; })
      .then(data => { if (!cancelled) setHistory(data); })
      .catch(cause => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Ошибка истории расчётов."); });
    return () => { cancelled = true; };
  }, [vesselId]);

  function loadCourseExample() {
    const sample = courseExample();
    setName(sample.name); setRevision(sample.revision); setLbp(sample.lbp); setDensity(sample.density);
    setCoordinate(sample.coordinate); setLightship(sample.lightship); setItems(sample.items); setHydro(sample.hydro); setKnCurve(sample.kn);
    setResult(null); setError(""); setNotice("Загружены агрегированные значения из учебного примера. Перед запуском проверьте ссылки на первоисточники.");
  }

  async function calculate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    const payload = {
      vessel_id: vesselId, name, vessel_data_revision: revision, coordinate_convention: coordinate,
      lbp_m: n(lbp), seawater_density_t_m3: n(density),
      lightship: {
        mass_t: n(lightship.mass_t), lcg_m: n(lightship.lcg_m), tcg_m: n(lightship.tcg_m), vcg_m: n(lightship.vcg_m),
        source_reference: lightship.source_reference,
        ...(lightship.forward_strength_moment_tm.trim() && lightship.strength_source_reference.trim()
          ? { forward_strength_moment_tm: n(lightship.forward_strength_moment_tm), strength_source_reference: lightship.strength_source_reference }
          : {}),
      },
      items: items.map(item => ({
        name: item.name, mass_t: n(item.mass_t), lcg_m: n(item.lcg_m), tcg_m: n(item.tcg_m), vcg_m: n(item.vcg_m),
        free_surface_moment_tm: n(item.free_surface_moment_tm || "0"), source_reference: item.source_reference,
      })),
      hydrostatic_table: hydro.map(row => ({
        displacement_volume_m3: n(row.displacement_volume_m3), draft_extreme_m: n(row.draft_extreme_m),
        lcf_from_ap_m: n(row.lcf_from_ap_m), lcb_from_ap_m: n(row.lcb_from_ap_m),
        transverse_metacentre_z_m: n(row.transverse_metacentre_z_m), mct_t_m_per_cm: n(row.mct_t_m_per_cm),
        source_reference: row.source_reference,
      })),
      ...(knCurve.length ? { kn_curve: knCurve.map(row => ({
        heel_angle_deg: n(row.heel_angle_deg), kn_m: n(row.kn_m), source_reference: row.source_reference,
      })) } : {}),
    };
    try {
      const response = await fetch(`${API}/calculations/loading-condition`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(responseError(body, `Расчёт не выполнен (HTTP ${response.status}). Проверьте исходные данные.`));
      setResult(body as RunDetails); setNotice("Расчёт выполнен и сохранён в истории как ESTIMATE_ONLY.");
      const historyResponse = await fetch(`${API}/vessels/${encodeURIComponent(vesselId)}/calculation-runs`);
      if (historyResponse.ok) setHistory(await historyResponse.json() as RunSummary[]);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Ошибка расчёта."); }
    finally { setBusy(false); }
  }

  async function openRun(id: string) {
    setError("");
    try {
      const response = await fetch(`${API}/calculation-runs/${encodeURIComponent(id)}`);
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(responseError(body, `Не удалось открыть расчёт (HTTP ${response.status}).`));
      setResult(body as RunDetails);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Ошибка истории расчётов."); }
  }

  const updateItem = (index: number, key: keyof WeightForm, value: string) => setItems(current => current.map((row, i) => i === index ? { ...row, [key]: value } : row));
  const updateHydro = (index: number, key: keyof HydroForm, value: string) => setHydro(current => current.map((row, i) => i === index ? { ...row, [key]: value } : row));
  const updateKn = (index: number, key: keyof KnForm, value: string) => setKnCurve(current => current.map((row, i) => i === index ? { ...row, [key]: value } : row));
  const o = result?.calculation_result.outputs;

  return <>
    <div className="page-heading"><div><div className="eyebrow">РАСЧЁТНЫЙ МОДУЛЬ</div><h1>Расчёт загрузки</h1><p>Водоизмещение, центр тяжести, осадки, дифферент, начальная GM, крен и, если задана KN, диаграмма GZ.</p></div><button type="button" className="secondary-button" onClick={loadCourseExample}>Загрузить пример из КП</button></div>
    <div className="notice"><span className="notice-icon">!</span><div><strong>Результат предварительный — ESTIMATE_ONLY</strong><p>Расчёт не является одобренным loadicator. Для эксплуатации необходимы независимая проверка методики, исходных таблиц, критериев класса и результата.</p></div></div>
    {apiState !== "online" && <div className="inline-alert error">Нет подключения к локальному API.</div>}
    {error && <div className="inline-alert error">{error}</div>}{notice && <div className="inline-alert success">{notice}</div>}
    <form onSubmit={calculate}>
      <section className="panel vessel-form-panel">
        <div className="panel-heading"><div><div className="eyebrow">ОСНОВНЫЕ ВХОДНЫЕ ДАННЫЕ</div><h2>Загрузочное условие</h2></div></div>
        <div className="form-grid">
          <label>Судно<select required value={vesselId} onChange={event => { setVesselId(event.target.value); const vessel = vessels.find(v => v.id === event.target.value); if (vessel?.lbp_m) setLbp(String(vessel.lbp_m)); }}><option value="">Выберите судно</option>{vessels.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</select></label>
          <label>Название условия<input required value={name} onChange={event => setName(event.target.value)} maxLength={120} placeholder="Например, оптимальный план" /></label>
          <label>Ревизия исходных данных<input required value={revision} onChange={event => setRevision(event.target.value)} maxLength={80} placeholder="Документ и ревизия таблиц" /></label>
          <label>LBP, м<input required type="number" min="0.001" step="0.001" value={lbp} onChange={event => setLbp(event.target.value)} /></label>
          <label>Плотность забортной воды, т/м³<input required type="number" min="0.501" max="1.5" step="0.001" value={density} onChange={event => setDensity(event.target.value)} /></label>
          <label className="wide-field">Система координат и datum<input required value={coordinate} onChange={event => setCoordinate(event.target.value)} placeholder="Откуда начало; направления X/Y/Z; основная плоскость" /></label>
        </div>
      </section>
      <section className="panel vessel-form-panel">
        <div className="panel-heading"><div><div className="eyebrow">ПОРОЖНЕЕ СУДНО</div><h2>Масса и центр тяжести</h2></div></div>
        <div className="form-grid">
          {([ ["mass_t","Масса, т"], ["lcg_m","LCG от AP, м"], ["tcg_m","TCG от ДП, м"], ["vcg_m","VCG от ОП, м"] ] as [keyof LightshipForm,string][]).map(([key,label]) => <label key={key}>{label}<input required type="number" step="0.001" value={lightship[key]} onChange={event => setLightship(current => ({ ...current, [key]: event.target.value }))} /></label>)}
          <label className="wide-field">Источник данных порожнего судна<input required minLength={3} value={lightship.source_reference} onChange={event => setLightship(current => ({ ...current, source_reference: event.target.value }))} placeholder="Документ, страница и таблица" /></label>
          <label>Исходный момент +Mx, т·м (необязательно)<input type="number" step="0.001" value={lightship.forward_strength_moment_tm} onChange={event => setLightship(current => ({ ...current, forward_strength_moment_tm: event.target.value }))} /></label>
          <label>Источник +Mx<input minLength={3} value={lightship.strength_source_reference} onChange={event => setLightship(current => ({ ...current, strength_source_reference: event.target.value }))} placeholder="Обязателен, если задан момент" /></label>
        </div>
      </section>
      <section className="panel vessel-form-panel">
        <div className="panel-heading"><div><div className="eyebrow">ПЕРЕМЕННЫЕ НАГРУЗКИ</div><h2>Масса, координаты и свободная поверхность</h2></div><button type="button" className="secondary-button" onClick={() => setItems(current => [...current, blankWeight()])}>＋ Добавить нагрузку</button></div>
        {items.map((item,index) => <div className="load-item-editor" key={index}><div className="form-subheading">Нагрузка {index+1}</div><div className="form-grid">
          {([ ["name","Название"], ["mass_t","Масса, т"], ["lcg_m","LCG от AP, м"], ["tcg_m","TCG от ДП, м"], ["vcg_m","VCG от ОП, м"], ["free_surface_moment_tm","FSM, т·м"] ] as [keyof WeightForm,string][]).map(([key,label]) => <label key={key}>{label}<input required={key !== "free_surface_moment_tm"} type={key === "name" ? "text" : "number"} step={key === "name" ? undefined : "0.001"} value={item[key]} onChange={event => updateItem(index,key,event.target.value)} /></label>)}
          <label className="wide-field">Источник нагрузки / координат / FSM<input required minLength={3} value={item.source_reference} onChange={event => updateItem(index,"source_reference",event.target.value)} placeholder="Документ, страница, таблица и строка" /></label>
        </div>{items.length > 1 && <div className="form-actions"><button type="button" className="secondary-button" onClick={() => setItems(current => current.filter((_,i) => i !== index))}>Удалить нагрузку</button></div>}</div>)}
      </section>
      <section className="panel vessel-form-panel">
        <div className="panel-heading"><div><div className="eyebrow">ИСТОЧНИК ГИДРОСТАТИКИ</div><h2>Таблица осадка — водоизмещение</h2></div><button type="button" className="secondary-button" onClick={() => setHydro(current => [...current, blankHydro()])}>＋ Добавить строку</button></div>
        <p className="form-hint">Внесите минимум две соседние строки для расчётного объёмного водоизмещения. Экстраполяция запрещена. Значения и единицы должны совпадать с таблицей конкретного судна.</p>
        {hydro.map((row,index) => <div className="load-item-editor" key={index}><div className="form-subheading">Строка гидростатики {index+1}</div><div className="form-grid">
          {([ ["displacement_volume_m3","Объёмное водоизмещение, м³"], ["draft_extreme_m","Экстремальная осадка, м"], ["lcf_from_ap_m","LCF от AP, м"], ["lcb_from_ap_m","LCB от AP, м"], ["transverse_metacentre_z_m","KMT от ОП, м"], ["mct_t_m_per_cm","MCT, т·м/см"] ] as [keyof HydroForm,string][]).map(([key,label]) => <label key={key}>{label}<input required type="number" step="0.001" value={row[key]} onChange={event => updateHydro(index,key,event.target.value)} /></label>)}
          <label className="wide-field">Источник строки<input required minLength={3} value={row.source_reference} onChange={event => updateHydro(index,"source_reference",event.target.value)} placeholder="Документ, страница, таблица, осадка / строка" /></label>
        </div>{hydro.length > 2 && <div className="form-actions"><button type="button" className="secondary-button" onClick={() => setHydro(current => current.filter((_,i) => i !== index))}>Удалить строку</button></div>}</div>)}
      </section>
      <section className="panel vessel-form-panel">
        <div className="panel-heading"><div><div className="eyebrow">НЕОБЯЗАТЕЛЬНЫЙ НАБОР</div><h2>Кривая KN для расчёта GZ</h2></div><button type="button" className="secondary-button" onClick={() => setKnCurve(current => [...current, blankKn()])}>＋ Добавить точку</button></div>
        <p className="form-hint">Если исходная KN кривая сверена, добавьте значения по углу крена. Система вычислит GZ и площадь под кривой; автоматического заключения по критериям IMO/Class пока нет.</p>
        {knCurve.map((row,index) => <div className="load-item-editor" key={index}><div className="form-grid">
          <label>Угол крена, °<input required type="number" min="0" max="180" step="0.1" value={row.heel_angle_deg} onChange={event => updateKn(index,"heel_angle_deg",event.target.value)} /></label>
          <label>KN, м<input required type="number" step="0.001" value={row.kn_m} onChange={event => updateKn(index,"kn_m",event.target.value)} /></label>
          <label className="wide-field">Источник точки<input required minLength={3} value={row.source_reference} onChange={event => updateKn(index,"source_reference",event.target.value)} placeholder="Документ, страница, таблица и угол" /></label>
        </div><div className="form-actions"><button type="button" className="secondary-button" onClick={() => setKnCurve(current => current.filter((_,i) => i !== index))}>Удалить точку</button></div></div>)}
        <div className="form-actions"><button className="primary-button" disabled={busy || apiState !== "online" || !vesselId}>{busy ? "Вычисление…" : "Выполнить и сохранить расчёт"}</button></div>
      </section>
    </form>
    {result && o && <section className="panel calculation-results">
      <div className="panel-heading"><div><div className="eyebrow">{result.calculation_result.status} · {result.calculation_result.engine_version}</div><h2>{result.name}</h2><p className="form-hint">Запуск {result.id}</p></div><button type="button" className="secondary-button print-button" onClick={() => window.print()}>Распечатать / сохранить PDF</button></div>
      <div className="metric-grid">
        <Metric label="ВОДОИЗМЕЩЕНИЕ" value={`${fmt(o.displacement_t,1)} т`} detail={`${fmt(o.displacement_volume_m3,1)} м³ при ρ=${density}`} />
        <Metric label="ОСАДКА СРЕДНЯЯ" value={`${fmt(o.mean_draft_m,3)} м`} detail={`Экстремальная: ${fmt(o.draft_extreme_m,3)} м`} />
        <Metric label="ОСАДКИ НОС / КОРМА" value={`${fmt(o.forward_draft_m,3)} / ${fmt(o.aft_draft_m,3)} м`} detail={`Дифферент: ${fmt(o.trim_m,3)} м`} />
        <Metric label="ИСПРАВЛЕННАЯ GM" value={`${fmt(o.corrected_initial_gm_m,3)} м`} detail={`VCG с FSM: ${fmt(o.corrected_vcg_m,3)} м`} />
        <Metric label="КРЕН" value={`${fmt(o.heel_deg_port_positive,3)}°`} detail="Плюс — на левый борт" />
        <Metric label="ЦЕНТР ТЯЖЕСТИ" value={`LCG ${fmt(o.lcg_m,2)} м`} detail={`TCG ${fmt(o.tcg_m,3)} м · VCG ${fmt(o.vcg_m,3)} м`} />
        <Metric label="СВОБОДНЫЕ ПОВЕРХНОСТИ" value={`${fmt(o.free_surface_moment_tm,1)} т·м`} detail={`Поправка VCG: ${fmt(o.free_surface_vcg_correction_m,3)} м`} />
        <Metric label="+Mx ОТНОСИТЕЛЬНО МИДЕЛЯ" value={o.forward_strength_moment_tm == null ? "Не рассчитано" : `${fmt(o.forward_strength_moment_tm/1000,1)} кт·м`} detail={o.forward_strength_moment_tm == null ? "Не задан исходный момент порожнего судна" : "Результат без сравнения с допустимой диаграммой"} />
      </div>
      <p className="form-hint">Интерполяция: {result.calculation_result.interpolation.method}; рабочий диапазон ∇ {fmt(result.calculation_result.interpolation.table_volume_min_m3,1)}–{fmt(result.calculation_result.interpolation.table_volume_max_m3,1)} м³. Экстраполяция запрещена.</p>
      {result.calculation_result.stability_curve && <div className="stability-curve-result">
        <h3>Кривая статической остойчивости</h3>
        <div className="metric-grid"><Metric label="МАКСИМАЛЬНОЕ GZ" value={`${fmt(result.calculation_result.stability_curve.maximum_gz_m,3)} м`} detail={`При ${fmt(result.calculation_result.stability_curve.heel_angle_at_maximum_deg,1)}°`} /><Metric label="ПЛОЩАДЬ ДО 30°" value={`${fmt(result.calculation_result.stability_curve.area_to_30_deg_m_rad,3)} м·рад`} detail="Интеграл табличной GZ" /><Metric label="ПЛОЩАДЬ ДО 40°" value={`${fmt(result.calculation_result.stability_curve.area_to_40_deg_m_rad,3)} м·рад`} detail="Интеграл табличной GZ" /><Metric label="ПЛОЩАДЬ 30–40°" value={`${fmt(result.calculation_result.stability_curve.area_30_to_40_deg_m_rad,3)} м·рад`} detail="Интеграл табличной GZ" /></div>
        <div className="vessel-table-wrap"><table className="vessel-table"><thead><tr><th>Крен, °</th><th>KN, м</th><th>GZ, м</th><th>ДДО, м·рад</th></tr></thead><tbody>{result.calculation_result.stability_curve.points.map(point => <tr key={point.heel_angle_deg}><td>{fmt(point.heel_angle_deg,1)}</td><td>{fmt(point.kn_m,3)}</td><td>{fmt(point.gz_m,3)}</td><td>{fmt(point.dynamic_arm_m_rad,3)}</td></tr>)}</tbody></table></div>
        <p className="form-hint">{result.calculation_result.stability_curve.note}</p>
      </div>}
      <ul>{result.calculation_result.warnings.map((warning,index) => <li key={index}>{warning}</li>)}</ul>
      {result.calculation_input && <div className="calculation-provenance"><h3>Источники сохранённого расчёта</h3><p><strong>Система координат:</strong> {result.calculation_input.coordinate_convention}</p><ul><li>Порожнее судно: {result.calculation_input.lightship.source_reference}</li>{result.calculation_input.items.map((item,index) => <li key={`weight-${index}`}>{item.name}: {item.source_reference}</li>)}{result.calculation_input.hydrostatic_table.map((row,index) => <li key={`hydro-${index}`}>Гидростатика {index+1}: {row.source_reference}</li>)}{result.calculation_input.kn_curve?.map((point,index) => <li key={`kn-${index}`}>KN, точка {index+1}: {point.source_reference}</li>)}</ul></div>}
    </section>}
    <section className="panel vessel-list"><div className="panel-heading"><div><div className="eyebrow">НЕИЗМЕНЯЕМАЯ ИСТОРИЯ</div><h2>Сохранённые расчёты</h2></div></div>
      {!vesselId ? <div className="empty-state">Выберите судно.</div> : history.length === 0 ? <div className="empty-state">Расчётов пока нет.</div> : <div className="vessel-table-wrap"><table className="vessel-table"><thead><tr><th>Условие</th><th>Водоизмещение</th><th>Средняя осадка</th><th>Версия</th><th></th></tr></thead><tbody>{history.map(run => <tr key={run.id}><td><strong>{run.name}</strong><small>{new Date(run.created_at).toLocaleString("ru-RU")} · {run.status}</small></td><td>{fmt(run.displacement_t,1)} т</td><td>{fmt(run.mean_draft_m,3)} м</td><td>{run.engine_version}</td><td><button type="button" className="secondary-button" onClick={() => void openRun(run.id)}>Открыть</button></td></tr>)}</tbody></table></div>}
    </section>
  </>;
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) { return <div className="metric-card"><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>; }
