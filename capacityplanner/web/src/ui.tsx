import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Activity, ArrowDownToLine, ArrowUpRight, BarChart3, Check, ChevronRight, CircleHelp, Menu, Moon, RefreshCw, Search, Settings2, Sun, X, AlertTriangle } from 'lucide-react';
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, Bar } from 'recharts';

export type Point = { time: string; value?: number | null; median?: number | null; lower?: number | null; upper?: number | null; actual?: number | null; radiation?: number | null; stock?: number | null };
export type NavItem = { id: string; label: string; icon: ReactNode };
export const number = (value: number | null | undefined, digits = 1) => value == null ? '—' : new Intl.NumberFormat('it-IT', { maximumFractionDigits: digits }).format(value);
export const day = (value: string, hourly = false) => new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: 'short', ...(hourly ? { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Rome' } : { year: 'numeric', timeZone: 'UTC' }) }).format(new Date(value));

export function useStored<T>(key: string, initial: T): [T, (value: T) => void] {
  const [state, setState] = useState<T>(() => { try { return JSON.parse(localStorage.getItem(key) || 'null') ?? initial; } catch { return initial; } });
  const update = (value: T) => { setState(value); try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Storage can be unavailable. */ } };
  return [state, update];
}

export function usePage(items: NavItem[]) {
  const read = () => items.some(x => x.id === location.hash.slice(1)) ? location.hash.slice(1) : items[0].id;
  const [page, setPage] = useState(read);
  useEffect(() => { const update = () => setPage(read()); window.addEventListener('hashchange', update); return () => window.removeEventListener('hashchange', update); }, []);
  return [page, (value: string) => { location.hash = value; setPage(value); }] as const;
}

export async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  let value: { detail?: unknown };
  try { value = await r.json(); } catch { throw new Error('Risposta del server non valida. Verifica che API e frontend siano avviati.'); }
  if (!r.ok) {
    const detail = value.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(x => `${x.loc?.slice(1).join('.') || 'Parametro'}: ${x.msg}`).join(' · ') : `Errore HTTP ${r.status}`;
    throw new Error(message);
  }
  return value as T;
}

export function useForecast<T, C extends object>(initial: C) {
  const [data, setData] = useState<T | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [applied, setApplied] = useState<C | null>(null);
  const controller = useRef<AbortController | null>(null);
  const run = useCallback(async (config: C) => {
    controller.current?.abort();
    const current = new AbortController(); controller.current = current;
    setBusy(true); setError('');
    try {
      const result = await getJSON<T>('/api/forecast', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config), signal: current.signal });
      if (!current.signal.aborted) { setData(result); setApplied(config); }
    } catch (e) {
      if (!current.signal.aborted) setError(e instanceof Error ? e.message : 'Calcolo non disponibile');
    } finally { if (!current.signal.aborted) setBusy(false); }
  }, []);
  useEffect(() => { void run(initial); return () => controller.current?.abort(); }, []);
  return { data, busy, error, applied, run };
}

export function downloadCSV(name: string, rows: Record<string, unknown>[]) {
  if (!rows.length) return;
  const columns = [...new Set(rows.flatMap(row => Object.keys(row)))];
  const cell = (value: unknown) => {
    let text = value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
    if (typeof value === 'string' && /^\s*[=+\-@]/.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  const csv = '\uFEFF' + [columns.map(cell).join(','), ...rows.map(row => columns.map(key => cell(row[key])).join(','))].join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function Shell({ name, eyebrow, icon, accent, items, page, onPage, children, status }: { name: string; eyebrow: string; icon: ReactNode; accent: string; items: NavItem[]; page: string; onPage: (id: string) => void; children: ReactNode; status: string }) {
  const [theme, setTheme] = useStored<'light' | 'dark'>(name+'-theme', 'light');
  const [menu, setMenu] = useState(false);
  const [help, setHelp] = useState(false);
  useEffect(() => { document.documentElement.dataset.theme = theme; document.documentElement.dataset.accent = accent; document.title = `${name} · aheadlab`; }, [theme, accent, name]);
  useEffect(() => { if (!menu && !help) return; const key = (e: KeyboardEvent) => { if (e.key === 'Escape') { setMenu(false); setHelp(false); } }; window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key); }, [menu, help]);
  return <div className="layout">
    <a className="skip" href="#main">Vai al contenuto</a>
    {menu && <button className="scrim" aria-label="Chiudi navigazione" onClick={() => setMenu(false)} />}
    <aside className={`sidebar ${menu ? 'open' : ''}`}>
      <a className="brand" href="#overview" onClick={() => { onPage(items[0].id); setMenu(false); }}><span className="brand-symbol">{icon}</span><span>{name}<small>by aheadlab</small></span></a>
      <div className="workspace"><span className="workspace-icon">A</span><div>Workspace locale<small>Portfolio · ambiente controllato</small></div><Check size={14} /></div>
      <div className="nav-heading">WORKSPACE</div>
      <nav aria-label="Navigazione principale">{items.map(item => <button key={item.id} aria-current={page === item.id ? 'page' : undefined} onClick={() => { onPage(item.id); setMenu(false); }}>{item.icon}<span>{item.label}</span>{page === item.id && <span className="active-dot" />}</button>)}</nav>
      <div className="sidebar-bottom"><div className="engine"><span className="status-dot" /><div>Motore Python<small>CPU · API locale</small></div><Activity size={16}/></div><p>Dati dichiarati. Decisioni verificabili.</p><a href="/docs" target="_blank" rel="noreferrer">Documentazione API <ArrowUpRight size={14}/></a></div>
    </aside>
    <div className="body"><header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-menu" aria-label="Apri navigazione" onClick={() => setMenu(!menu)}><Menu size={20}/></button><span>{eyebrow}</span><ChevronRight size={14}/><strong>{items.find(i => i.id === page)?.label}</strong></div><div className="top-actions"><span className="environment">{status}</span><button className="icon-button" aria-label={theme === 'light' ? 'Attiva tema scuro' : 'Attiva tema chiaro'} onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>{theme === 'light' ? <Moon size={18}/> : <Sun size={18}/>}</button><button className="icon-button" aria-label="Informazioni workspace" onClick={() => setHelp(true)}><CircleHelp size={18}/></button><span className="avatar">AL</span></div></header>
    <main id="main">{children}<footer className="footer"><span>aheadlab / {name}</span><span>Locale · nessuna azione esterna automatica</span></footer></main></div>
    {help && <Dialog title="Un workspace, non una promessa" onClose={() => setHelp(false)}><p>Le elaborazioni usano le pipeline Python del progetto. Il badge sorgente distingue demo sintetica e replay di traffico CESNET. Capacità, deficit e costi sono simulati.</p><p>I modelli usano pesi già presenti nella cache locale. Il server esegue un calcolo alla volta. Interrompere la pagina non cancella un'inferenza già iniziata.</p><p>Le impostazioni di interfaccia rimangono in questo browser. Non sono presenti account multiutente o invii automatici.</p><a className="button secondary" href="/docs" target="_blank" rel="noreferrer">Apri OpenAPI <ArrowUpRight size={16}/></a></Dialog>}
  </div>;
}

export function Heading({ label, title, description, action }: { label: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{label}</div><h1>{title}</h1><p>{description}</p></div>{action && <div className="heading-action">{action}</div>}</div>;
}
export function Kpi({ label, value, unit, note, icon, emphasis = false }: { label: string; value: string; unit?: string; note: string; icon: ReactNode; emphasis?: boolean }) {
  return <section className={`kpi ${emphasis ? 'emphasis' : ''}`}><div className="kpi-top"><span>{label}</span><span className="kpi-icon">{icon}</span></div><div className="kpi-value">{value}<small>{unit}</small></div><div className="kpi-note">{note}</div></section>;
}
export function Panel({ title, subtitle, action, children, className = '' }: { title: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}
export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'positive' | 'warning' | 'danger' }) { return <span className={`badge ${tone}`}>{children}</span>; }
export function Notice({ children, danger = false }: { children: ReactNode; danger?: boolean }) { return <div className={`notice ${danger ? 'danger' : ''}`} role={danger ? 'alert' : undefined}><AlertTriangle size={16}/><div>{children}</div></div>; }
export function Empty({ title, children }: { title: string; children: ReactNode }) { return <div className="empty"><BarChart3 size={30}/><h3>{title}</h3><p>{children}</p></div>; }
export function Loading({ error, busy, retry }: { error: string; busy: boolean; retry: () => void }) { return <>{busy && <div className="loading" role="status"><RefreshCw className="spin" size={19}/><div><strong>Elaborazione in corso</strong><span>Caricamento del modello locale e calcolo della previsione. Le selezioni restano disponibili.</span></div></div>}{error && <Notice danger><strong>Operazione non completata</strong><p>{error}</p><button className="button secondary small" disabled={busy} onClick={retry}>Riprova</button></Notice>}</>; }
export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) { return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>; }
export function Apply({ busy, dirty }: { busy: boolean; dirty: boolean }) { return <button className="button primary" type="submit" disabled={busy}><RefreshCw size={16} className={busy ? 'spin' : ''}/>{busy ? 'Calcolo in corso' : dirty ? 'Applica parametri' : 'Aggiorna analisi'}</button>; }
export function SearchBox({ value, onChange, placeholder = 'Cerca...' }: { value: string; onChange: (text: string) => void; placeholder?: string }) { return <div className="search"><Search size={17}/><input aria-label={placeholder} placeholder={placeholder} value={value} onChange={e => onChange(e.target.value)}/>{value && <button className="icon-button" aria-label="Svuota ricerca" onClick={() => onChange('')}><X size={15}/></button>}</div>; }
export function ExportButton({ label = 'Esporta CSV', name, rows, disabled = false }: { label?: string; name: string; rows: Record<string, unknown>[]; disabled?: boolean }) { return <button className="button secondary" disabled={disabled || !rows.length} onClick={() => downloadCSV(name, rows)}><ArrowDownToLine size={16}/>{label}</button>; }

export function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close(); }, []);
  return <dialog ref={ref} className="dialog" onCancel={onClose} onClick={e => { if (e.target === ref.current) onClose(); }}><div className="dialog-head"><h2>{title}</h2><button className="icon-button" aria-label="Chiudi dettaglio" onClick={onClose}><X size={20}/></button></div><div className="dialog-content">{children}</div></dialog>;
}

export function ForecastChart({ history = [], forecast, unit, hourly = false, radiation = false, showStock = false }: { history?: Point[]; forecast: Point[]; unit: string; hourly?: boolean; radiation?: boolean; showStock?: boolean }) {
  const [showHistory, setShowHistory] = useState(true);
  const [band, setBand] = useState(true);
  const points = [...(showHistory ? history : []), ...forecast].map(p => ({ ...p, label: hourly ? day(p.time, true) : new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: 'short', timeZone: 'UTC' }).format(new Date(p.time)), interval: p.lower != null && p.upper != null ? [p.lower, p.upper] : undefined }));
  const hasBand = forecast.some(p => p.lower != null);
  return <><div className="chart-controls">{history.length > 0 && <label><input type="checkbox" checked={showHistory} onChange={e => setShowHistory(e.target.checked)}/>Storico</label>}{hasBand && <label><input type="checkbox" checked={band} onChange={e => setBand(e.target.checked)}/>Intervallo 10–90%</label>}<span>{unit}{hourly ? ' · Europe/Rome' : ''}</span></div><div className="chart" role="img" aria-label={`Grafico interattivo previsione in ${unit}`}><ResponsiveContainer width="100%" height="100%"><ComposedChart data={points} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="var(--line)"/><XAxis dataKey="label" minTickGap={55} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={false} tickLine={false}/><YAxis tick={{ fill: 'var(--muted)', fontSize: 11 }} width={48} axisLine={false} tickLine={false}/>{radiation && <YAxis yAxisId="weather" orientation="right" hide/>}<Tooltip contentStyle={{ background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 12, color: 'var(--text)' }} formatter={(value, name) => [Array.isArray(value) ? value.map(v => number(Number(v))).join(' – ') : number(Number(value), 2), name]}/><Legend wrapperStyle={{ fontSize: 11, paddingTop: 14 }}/>{radiation && <Bar yAxisId="weather" dataKey="radiation" name="Radiazione W/m²" fill="var(--accent)" opacity={0.12} radius={[2,2,0,0]} isAnimationActive={false}/>}<Line type="monotone" dataKey="value" name="Storico" legendType={history.length && showHistory ? 'line' : 'none'} stroke="var(--muted)" dot={false} strokeWidth={1.7} isAnimationActive={false}/>{hasBand && band && <Area type="monotone" dataKey="interval" name="p10–p90" fill="var(--accent)" stroke="none" fillOpacity={0.14} isAnimationActive={false}/>}<Line type="monotone" dataKey="median" name="Previsione" stroke="var(--accent)" dot={false} strokeWidth={2.6} isAnimationActive={false}/>{showStock && <Line type="monotone" dataKey="stock" name="Giacenza senza arrivi" stroke="#9a6cf4" dot={false} strokeWidth={1.8} isAnimationActive={false}/>}</ComposedChart></ResponsiveContainer></div></>;
}

type ReportIndex = { reports: { id: string; label: string; metadata: Record<string, unknown> }[] };
type Report = { id: string; metadata: Record<string, unknown>; tables: Record<string, Record<string, unknown>[]> };
export function Reports({ prefix }: { prefix: string }) {
  const [reports, setReports] = useState<ReportIndex['reports']>([]);
  const [selected, setSelected] = useStored(prefix+'-report', '');
  const [report, setReport] = useState<Report | null>(null);
  const [table, setTable] = useState('');
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState(0);
  const [reload, setReload] = useState(0);
  const [indexBusy, setIndexBusy] = useState(true);
  useEffect(() => { let live = true; setIndexBusy(true); setError(''); getJSON<ReportIndex>('/api/reports').then(x => { if (!live) return; setReports(x.reports); if (!x.reports.some(r => r.id === selected)) setSelected(x.reports[0]?.id || ''); }).catch(e => { if (live) setError(e.message); }).finally(() => { if (live) setIndexBusy(false); }); return () => { live = false; }; }, [reload]);
  useEffect(() => { setReport(null); if (!selected) { setBusy(false); return; } const control = new AbortController(); setBusy(true); setError(''); getJSON<Report>('/api/reports/'+encodeURIComponent(selected), {signal: control.signal}).then(x => { if (control.signal.aborted) return; setReport(x); setTable(Object.keys(x.tables).find(k => ['summary','riepilogo','anomalies'].includes(k)) || Object.keys(x.tables)[0] || ''); setPage(0); }).catch(e => { if (!control.signal.aborted) setError(e.message); }).finally(() => { if (!control.signal.aborted) setBusy(false); }); return () => control.abort(); }, [selected, reload]);
  const rows = (report?.tables[table] || []).filter(r => Object.values(r).some(v => String(v ?? '').toLowerCase().includes(query.toLowerCase())));
  const columns = Object.keys(rows[0] || report?.tables[table]?.[0] || {});
  return <><Heading label="VALIDAZIONE / DATI MISURATI" title="Risultati, non promesse." description="Confronti riproducibili. Controlla sempre sorgente e protocollo prima di interpretare le metriche."/>
    <Panel title="Esplora i benchmark" subtitle="I report sono calcolati dalle pipeline Python, non generati dal frontend."><div className="filter-bar"><Field label="Esecuzione"><select value={selected} onChange={e => { setSelected(e.target.value); setQuery(''); }}>{reports.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}</select></Field><Field label="Tabella"><select value={table} onChange={e => { setTable(e.target.value); setPage(0); }}>{Object.keys(report?.tables || {}).map(key => <option key={key}>{key}</option>)}</select></Field><SearchBox value={query} onChange={v => { setQuery(v); setPage(0); }} placeholder="Cerca nei risultati"/><ExportButton name={`${selected}-${table}.csv`} rows={rows}/></div><Loading busy={busy || indexBusy} error={error} retry={() => setReload(value => value + 1)}/>
    {!busy && rows.length > 0 ? <><div className="table-wrap"><table><thead><tr>{columns.map(c => <th key={c}>{c.replaceAll('_',' ')}</th>)}</tr></thead><tbody>{rows.slice(page*20, page*20+20).map((row,i) => <tr key={i}>{columns.map(c => <td key={c}>{typeof row[c] === 'number' ? number(row[c] as number, 4) : String(row[c] ?? '—')}</td>)}</tr>)}</tbody></table></div><div className="pagination"><span>{rows.length} risultati · pagina {page+1} di {Math.max(1,Math.ceil(rows.length/20))}</span><div><button className="button secondary small" disabled={page === 0} onClick={() => setPage(page-1)}>Precedente</button><button className="button secondary small" disabled={(page+1)*20 >= rows.length} onClick={() => setPage(page+1)}>Successiva</button></div></div></> : !busy && !error && <Empty title="Nessun risultato">Prova un altro filtro o genera un report con la CLI del progetto.</Empty>}</Panel>
    {report && <Panel title="Protocollo dell'esecuzione" subtitle="Provenienza, contesto e assunzioni del confronto"><div className="metadata-grid">{Object.entries(report.metadata).map(([key,value]) => <div key={key}><span>{key.replaceAll('_',' ')}</span><strong>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</strong></div>)}</div></Panel>}
  </>;
}
