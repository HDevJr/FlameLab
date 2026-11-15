// BL-17.2: formulário dinâmico guiado por contrato tipado. Valores ficam como texto durante a edição;
// `toWire` converte para o formato do servidor (números finitos ou null). A validação física é do servidor.
import type { Contract, ContractField, Conversion, FieldIssue } from "./api";

export type Payload = Record<string, unknown>;
type Row = Record<string, unknown>;
const isObj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);

export function visible(f: ContractField, scope: Row) {
  return !f.when || f.when.in.includes(String(scope[f.when.field] ?? ""));
}

function columnDimensionUnits(f: ContractField, row: Row, columns: ContractField[]) {
  if (!f.dimension_from) return { units: f.units ?? [], si: f.si_unit ?? "" };
  const opt = columns.find((c) => c.name === f.dimension_from)?.options?.find((o) => o.value === row[f.dimension_from!]);
  return { units: opt?.units ?? [], si: opt?.si_unit ?? "" };
}

function emptyFor(f: ContractField, scope: Row, columns: ContractField[]): unknown {
  if (f.type === "quantity") return { value: "", unit: columnDimensionUnits(f, scope, columns).si || f.si_unit || "" };
  if (f.type === "vector") return { x: "", y: "", z: "", unit: f.si_unit ?? "" };
  if (f.type === "rows") return [];
  return "";
}

export function emptyPayload(contract: Contract): Payload {
  const out: Payload = {};
  for (const f of contract.fields) out[f.name] = emptyFor(f, out, contract.fields);
  return out;
}

const num = (s: unknown) => (s === "" || s === null || s === undefined ? null : Number(s));

function wireValue(f: ContractField, v: unknown, scope: Row, columns: ContractField[]): unknown {
  if (f.type === "quantity" && isObj(v)) return { value: num(v.value), unit: String(v.unit ?? "") };
  if (f.type === "vector" && isObj(v)) return { x: num(v.x), y: num(v.y), z: num(v.z), unit: String(v.unit ?? "") };
  if (f.type === "rows" && Array.isArray(v)) return v.map((row: Row) => wireObject(f.columns ?? [], row));
  void scope; void columns;
  return v;
}

function wireObject(fields: ContractField[], scope: Row): Payload {
  const out: Payload = {};
  for (const f of fields) {
    if (!visible(f, scope)) continue;
    const w = wireValue(f, scope[f.name], scope, fields);
    if (w === "" || w === undefined) continue;
    if (f.type === "quantity" && isObj(w) && w.value === null) continue;
    if (f.type === "vector" && isObj(w) && w.x === null && w.y === null && w.z === null) continue;
    if (f.type === "rows" && Array.isArray(w) && !w.length) continue;
    out[f.name] = w;
  }
  return out;
}

export const toWire = (contract: Contract, payload: Payload) => wireObject(contract.fields, payload);

/** Valores sintéticos do modo TESTE: respeitam tipos, dimensões, unidades e limites básicos. */
export function syntheticPayload(contract: Contract): Payload {
  const text = (f: ContractField) => "TESTE — conteúdo sintético para verificar a interface".padEnd(Math.max(f.min ?? 2, 10), ".");
  let counter = 0; // valores crescentes: intervalos (início < fim) e séries temporais ficam coerentes
  const qty = (f: ContractField, si: string) => {
    counter += 1;
    if (si === "K") return { value: String(290 + counter), unit: "K" };
    return { value: String(f.max != null ? f.max / (counter + 1) : counter), unit: si };
  };
  function fill(fields: ContractField[], into: Row, rowIndex = 0) {
    for (const f of fields) {
      if (!visible(f, into)) continue;
      if (f.type === "enum") into[f.name] = (f.options ?? [])[Math.min(rowIndex, (f.options?.length ?? 1) - 1)]?.value ?? "";
      else if (f.type === "text") into[f.name] = text(f);
      else if (f.type === "quantity") into[f.name] = qty(f, columnDimensionUnits(f, into, fields).si || f.si_unit || "");
      else if (f.type === "vector") into[f.name] = { x: "0", y: "0", z: "0", unit: f.si_unit ?? "m" };
      else if (f.type === "rows") {
        const n = Math.max(f.min_rows ?? 0, f.required ? 1 : 0);
        into[f.name] = Array.from({ length: n }, (_, i) => { const r: Row = {}; fill(f.columns ?? [], r, i); return r; });
      }
    }
  }
  const out: Payload = {};
  fill(contract.fields, out);
  return out;
}

function Issues({ path, errors }: { path: string; errors: FieldIssue[] }) {
  const mine = errors.filter((e) => e.field === path);
  return mine.length ? <span className="field-error" role="alert">{mine.map((e) => e.message_pt).join(" ")}</span> : null;
}

function conv(path: string, conversions: Conversion[]) {
  const c = conversions.find((x) => x.field === path);
  return c ? <small className="conversion">{c.original} = <strong>{c.si}</strong> (SI)</small> : null;
}

function FieldInput({ f, value, onChange, scope, columns, path, errors, conversions, disabled }: {
  f: ContractField; value: unknown; onChange: (v: unknown) => void; scope: Row; columns: ContractField[]; path: string;
  errors: FieldIssue[]; conversions: Conversion[]; disabled?: boolean;
}) {
  const req = f.required ? " *" : " (opcional)";
  if (f.type === "enum") return <label className={errors.some((e) => e.field === path) ? "invalid" : ""}>{f.label_pt}{req}
    <select value={String(value ?? "")} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
      <option value="">Selecione…</option>{(f.options ?? []).map((o) => <option key={o.value} value={o.value}>{o.label_pt}</option>)}
    </select>{f.help_pt && <small>{f.help_pt}</small>}<Issues path={path} errors={errors} /></label>;
  if (f.type === "text") return <label className={`${f.multiline ? "wide" : ""} ${errors.some((e) => e.field === path) ? "invalid" : ""}`}>{f.label_pt}{req}
    {f.multiline ? <textarea rows={2} value={String(value ?? "")} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
      : <input type="text" value={String(value ?? "")} disabled={disabled} onChange={(e) => onChange(e.target.value)} />}
    {f.help_pt && <small>{f.help_pt}</small>}<Issues path={path} errors={errors} /></label>;
  if (f.type === "quantity") {
    const q = isObj(value) ? value : { value: "", unit: "" };
    const { units, si } = columnDimensionUnits(f, scope, columns);
    const invalid = errors.some((e) => e.field === path);
    return <div className={`quantity ${invalid ? "invalid" : ""}`}>
      <label>{f.label_pt}{req}<input type="number" step="any" value={String(q.value ?? "")} disabled={disabled} onChange={(e) => onChange({ ...q, value: e.target.value })} /></label>
      <label>Unidade{f.dimension_pt ? ` (${f.dimension_pt})` : ""}<select value={String(q.unit ?? "")} disabled={disabled || !units.length} onChange={(e) => onChange({ ...q, unit: e.target.value })}>
        {!units.length && <option value="">escolha a grandeza</option>}
        {units.map((u) => <option key={u.value} value={u.value}>{u.label_pt}</option>)}</select></label>
      <small>{si ? `Canônica: ${si}` : ""}{f.min != null ? ` · ${f.min_exclusive === false ? "≥" : ">"} ${f.min}` : ""}{f.max != null ? ` · ≤ ${f.max}` : ""}</small>
      {conv(path, conversions)}{f.help_pt && <small>{f.help_pt}</small>}<Issues path={path} errors={errors} />
    </div>;
  }
  if (f.type === "vector") {
    const v = isObj(value) ? value : { x: "", y: "", z: "", unit: f.si_unit ?? "" };
    return <fieldset className="vector"><legend>{f.label_pt}{req}</legend>
      {(f.axes ?? ["x", "y", "z"]).map((a) => <label key={a}>{a}<input type="number" step="any" value={String(v[a] ?? "")} disabled={disabled} onChange={(e) => onChange({ ...v, [a]: e.target.value })} />
        <Issues path={`${path}.${a}`} errors={errors} /></label>)}
      <label>Unidade<select value={String(v.unit ?? "")} disabled={disabled} onChange={(e) => onChange({ ...v, unit: e.target.value })}>
        {(f.units ?? []).map((u) => <option key={u.value} value={u.value}>{u.label_pt}</option>)}</select></label>
      {f.help_pt && <small>{f.help_pt}</small>}<Issues path={path} errors={errors} />
    </fieldset>;
  }
  // rows
  const list: Row[] = Array.isArray(value) ? value as Row[] : [];
  const cols = f.columns ?? [];
  const max = f.max_rows ?? 30;
  return <fieldset className="rows wide"><legend>{f.label_pt}{req}{f.min_rows ? ` — mínimo ${f.min_rows} linha(s)` : ""}</legend>
    {f.help_pt && <p className="detail">{f.help_pt}</p>}
    {list.map((row, i) => <div className="row-item" key={i}>
      <strong>Linha {i + 1}</strong>
      {cols.filter((c) => visible(c, row)).map((c) => <FieldInput key={c.name} f={c} value={row[c.name]} scope={row} columns={cols} path={`${path}[${i}].${c.name}`}
        errors={errors} conversions={conversions} disabled={disabled}
        onChange={(v) => {
          const next = { ...row, [c.name]: v };
          // trocar a grandeza/propriedade troca a dimensão: a unidade volta para a canônica da nova dimensão
          if (c.type === "enum") for (const q of cols) if (q.dimension_from === c.name)
            next[q.name] = { value: (isObj(row[q.name]) ? row[q.name] as Row : {}).value ?? "", unit: c.options?.find((o) => o.value === v)?.si_unit ?? "" };
          onChange(list.map((r, j) => (j === i ? next : r)));
        }} />)}
      <button type="button" disabled={disabled} onClick={() => onChange(list.filter((_, j) => j !== i))}>Remover linha {i + 1}</button>
    </div>)}
    <button type="button" disabled={disabled || list.length >= max} onClick={() => { const r: Row = {}; for (const c of cols) r[c.name] = emptyFor(c, r, cols); onChange([...list, r]); }}>
      Adicionar linha</button>{list.length >= max && <small> Limite de {max} linha(s) atingido.</small>}
    <Issues path={path} errors={errors} />
  </fieldset>;
}

export default function StructuredForm({ contract, value, onChange, errors = [], conversions = [], disabled }: {
  contract: Contract; value: Payload; onChange: (v: Payload) => void; errors?: FieldIssue[]; conversions?: Conversion[]; disabled?: boolean;
}) {
  return <fieldset className="structured form wide" aria-label={`Formulário: ${contract.title_pt}`}>
    <legend>{contract.kind_pt}: {contract.title_pt}</legend>
    {contract.intro_pt && <p className="box info wide">{contract.intro_pt}</p>}
    {contract.fields.filter((f) => visible(f, value)).map((f) => <FieldInput key={f.name} f={f} value={value[f.name]} scope={value} columns={contract.fields} path={f.name}
      errors={errors} conversions={conversions} disabled={disabled} onChange={(v) => onChange({ ...value, [f.name]: v })} />)}
  </fieldset>;
}
