import type { ContractAnalysisData } from './types';
import { formatDate } from '../../../utils/formatDate';

type RGB = [number, number, number];

// ── Paleta ────────────────────────────────────────────────────────────────────
const NAVY:     RGB = [15,  23,  42];   // fondo portada
const NAVYMID:  RGB = [30,  41,  59];   // fondo tarjeta
const NAVYDECO: RGB = [22,  34,  58];   // formas decorativas
const NAVYLINE: RGB = [51,  65,  85];   // líneas sobre fondo oscuro
const BLUE:     RGB = [59,  130, 246];  // color de marca
const BLIGHT:   RGB = [219, 234, 254];  // fondo azul tenue
const WHITE:    RGB = [255, 255, 255];
const LGRAY:    RGB = [248, 250, 252];  // fondo sección clara
const BORDER:   RGB = [226, 232, 240];
const TMAIN:    RGB = [15,  23,  42];
const TMUTED:   RGB = [100, 116, 139];
const S400:     RGB = [148, 163, 184];  // slate-400 sobre oscuro
const RED:      RGB = [220, 38,  38];
const REDBG:    RGB = [254, 226, 226];
const AMBER:    RGB = [217, 119, 6];
const AMBERBG:  RGB = [254, 243, 199];
const GREEN:    RGB = [22,  163, 74];
const GREENBG:  RGB = [220, 252, 231];
const ORANGE:   RGB = [234, 88,  12];
const ORANGEBG: RGB = [255, 237, 213];

// ── Etiquetas de tipo de contrato ─────────────────────────────────────────────
const CONTRACT_TYPE_LABELS: Record<string, Record<string, string>> = {
  es: {
    arrendamiento_vivienda: 'Arrendamiento de vivienda',
    arrendamiento_local:    'Arrendamiento de local',
    prestacion_servicios:   'Prestación de servicios',
  },
  en: {
    arrendamiento_vivienda: 'Residential lease',
    arrendamiento_local:    'Commercial lease',
    prestacion_servicios:   'Service agreement',
  },
  fr: {
    arrendamiento_vivienda: 'Bail résidentiel',
    arrendamiento_local:    'Bail commercial',
    prestacion_servicios:   'Contrat de services',
  },
  de: {
    arrendamiento_vivienda: 'Wohnungsmietvertrag',
    arrendamiento_local:    'Gewerbemietvertrag',
    prestacion_servicios:   'Dienstleistungsvertrag',
  },
  pt: {
    arrendamiento_vivienda: 'Arrendamento habitacional',
    arrendamiento_local:    'Arrendamento comercial',
    prestacion_servicios:   'Prestação de serviços',
  },
};

function labelContractType(key: string, lang = 'es'): string {
  return CONTRACT_TYPE_LABELS[lang]?.[key] ?? CONTRACT_TYPE_LABELS['es']?.[key] ?? key;
}

// ── Cargador de logo ──────────────────────────────────────────────────────────
interface Logo { base64: string; aspect: number }

async function tryFetchLogo(path: string): Promise<Logo | null> {
  try {
    const res = await fetch(path);
    if (!res.ok) return null;
    const blob = await res.blob();
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload  = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
    const aspect = await new Promise<number>((resolve) => {
      const img = new Image();
      img.onload  = () => resolve(img.naturalWidth / (img.naturalHeight || 1) || 3.3);
      img.onerror = () => resolve(3.3);
      img.src = dataUrl;
      setTimeout(() => resolve(3.3), 3000);
    });
    return { base64: dataUrl, aspect: Math.max(0.5, Math.min(10, aspect)) };
  } catch {
    return null;
  }
}

async function loadLogo(): Promise<Logo | null> {
  // logo-dark tiene texto blanco sobre fondo transparente, ideal para la portada oscura
  return (await tryFetchLogo('/logo-dark.png')) ?? (await tryFetchLogo('/logo.png')) ?? null;
}

// ── Generador de PDF ──────────────────────────────────────────────────────────
export async function createContractAnalysisPdf(data: ContractAnalysisData): Promise<void> {
  const { default: jsPDF } = await import('jspdf');
  const pdf  = new jsPDF('p', 'mm', 'a4');
  const W    = pdf.internal.pageSize.getWidth();   // 210 mm
  const H    = pdf.internal.pageSize.getHeight();  // 297 mm
  const M    = 18;                                 // margen
  const CW   = W - M * 2;                          // ancho de contenido 174 mm

  // Atajos
  const fill   = (c: RGB)               => pdf.setFillColor(c[0], c[1], c[2]);
  const stroke = (c: RGB)               => pdf.setDrawColor(c[0], c[1], c[2]);
  const clr    = (c: RGB)               => pdf.setTextColor(c[0], c[1], c[2]);
  const fnt    = (s: 'normal'|'bold'|'italic', sz: number) => {
    pdf.setFont('helvetica', s);
    pdf.setFontSize(sz);
  };
  const wrap = (t: string, maxW: number) => pdf.splitTextToSize(t, maxW) as string[];

  const logo = await loadLogo();

  // ══════════════════════════════════════════════════════════════════
  // PORTADA
  // ══════════════════════════════════════════════════════════════════

  fill(NAVY);
  pdf.rect(0, 0, W, H, 'F');

  fill(NAVYDECO);
  pdf.circle(W + 8, 15, 72, 'F');
  pdf.circle(-12, H - 35, 58, 'F');

  fill(BLUE);
  pdf.rect(0, 0, W, 4, 'F');

  // ── Logo (y=28) ──────────────────────────────────────────────────
  const LOGO_MAX_W = 68;
  const LOGO_MAX_H = 28;
  let afterLogoY = 36;

  if (logo) {
    const rawH = LOGO_MAX_W / logo.aspect;
    const logoW = rawH > LOGO_MAX_H ? LOGO_MAX_W * (LOGO_MAX_H / rawH) : LOGO_MAX_W;
    const logoH = rawH > LOGO_MAX_H ? LOGO_MAX_H : rawH;
    const logoX = (W - logoW) / 2;
    pdf.addImage(logo.base64, 'PNG', logoX, 26, logoW, logoH);
    afterLogoY = 26 + logoH + 12;
  } else {
    fnt('bold', 18);
    clr(BLUE);
    pdf.text('ContratIA', W / 2, 38, { align: 'center' });
    afterLogoY = 50;
  }

  // ── Línea de acento azul ─────────────────────────────────────────
  fill(BLUE);
  pdf.rect((W - 48) / 2, afterLogoY, 48, 1.2, 'F');
  afterLogoY += 13;

  // ── Título principal ─────────────────────────────────────────────
  fnt('bold', 25);
  clr(WHITE);
  pdf.text('INFORME DE ANÁLISIS', W / 2, afterLogoY, { align: 'center' });
  afterLogoY += 11;
  pdf.text('DE CONTRATO', W / 2, afterLogoY, { align: 'center' });
  afterLogoY += 11;

  // ── Subtítulo ────────────────────────────────────────────────────
  fnt('italic', 9.5);
  clr(S400);
  pdf.text('Análisis jurídico asistido por inteligencia artificial', W / 2, afterLogoY, { align: 'center' });
  afterLogoY += 16;

  // ── Separador decorativo ─────────────────────────────────────────
  fill(NAVYLINE);
  pdf.rect(M + 22, afterLogoY, CW - 44, 0.5, 'F');
  afterLogoY += 14;

  // ── Tarjeta de información del contrato ──────────────────────────
  const CPAD = 12;
  const CX   = M + 4;
  const CWC  = CW - 8;
  const fnLines = wrap(data.filename, CWC - CPAD * 2 - 6);

  let cardH = CPAD * 1.5 + 8;
  cardH += fnLines.length * 7.5;
  cardH += 8;
  if (data.contractType)   cardH += 7;
  cardH += CPAD;

  fill(NAVYMID);
  pdf.roundedRect(CX, afterLogoY, CWC, cardH, 4, 4, 'F');
  fill(BLUE);
  pdf.roundedRect(CX, afterLogoY, 4, cardH, 2, 2, 'F');

  let cy = afterLogoY + CPAD;

  fnt('bold', 7);
  clr(S400);
  pdf.text('CONTRATO', CX + CPAD, cy);
  cy += 7;

  fnt('bold', 13);
  clr(WHITE);
  fnLines.forEach(line => { pdf.text(line, CX + CPAD, cy); cy += 7.5; });
  cy += 2;

  fnt('normal', 9);
  clr(S400);
  pdf.text(`Fecha de análisis: ${data.uploadDate}`, CX + CPAD, cy);
  cy += 7;

  if (data.contractType) {
    pdf.text(`Tipo: ${labelContractType(data.contractType, data.language)}`, CX + CPAD, cy);
    cy += 7;
  }

  cy += 2;

  // ── Insignia de riesgo ───────────────────────────────────────────
  const riskBadgeColor: Record<string, RGB>   = { high: RED, medium: AMBER, low: GREEN };
  const riskBadgeLabel: Record<string, string> = { high: 'RIESGO ALTO', medium: 'RIESGO MEDIO', low: 'RIESGO BAJO' };
  const rc = riskBadgeColor[data.riskLevel] ?? NAVYLINE;

  fill(rc);
  pdf.roundedRect(CX + CPAD, cy - 1, 44, 9, 2, 2, 'F');
  fnt('bold', 8.5);
  clr(WHITE);
  pdf.text(riskBadgeLabel[data.riskLevel] ?? 'N/A', CX + CPAD + 22, cy + 5.5, { align: 'center' });

  // ── Pie de portada ───────────────────────────────────────────────
  fill(NAVYLINE);
  pdf.rect(M + 10, H - 16, CW - 20, 0.3, 'F');
  fnt('normal', 7.5);
  clr([71, 85, 105] as RGB);
  pdf.text(
    `ContratIA (c) ${new Date().getFullYear()}  -  Documento de uso confidencial  -  Generado con inteligencia artificial`,
    W / 2, H - 9, { align: 'center' }
  );

  // ══════════════════════════════════════════════════════════════════
  // PÁGINAS INTERIORES
  // ══════════════════════════════════════════════════════════════════

  const newPage = (): number => {
    pdf.addPage();
    fill(BLUE);
    pdf.rect(0, 0, W, 2.5, 'F');
    fnt('normal', 7);
    clr(TMUTED);
    pdf.text('ContratIA', W - M, 9, { align: 'right' });
    return M + 8;
  };

  let y = newPage();

  const checkSpace = (need: number) => {
    if (y + need > H - M - 10) y = newPage();
  };

  const heading = (title: string, c: RGB) => {
    checkSpace(24);
    fill(c);
    pdf.rect(M, y, 4, 12, 'F');
    fnt('bold', 14);
    clr(c);
    pdf.text(title, M + 9, y + 9);
    y += 19;
  };

  const listItem = (idx: number, text: string) => {
    const lines = wrap(text, CW - 15);
    checkSpace(lines.length * 5.5 + 6);
    fill(LGRAY);
    pdf.circle(M + 4, y + 3.5, 4, 'F');
    fnt('bold', 8);
    clr(TMUTED);
    pdf.text(String(idx + 1), M + 4, y + 5, { align: 'center' });
    fnt('normal', 10);
    clr(TMAIN);
    lines.forEach((line, i) => pdf.text(line, M + 12, y + 5 + i * 5.5));
    y += lines.length * 5.5 + 5;
  };

  // ══════════════════════════════════════════════════════════════════
  // RESUMEN EJECUTIVO
  // ══════════════════════════════════════════════════════════════════

  heading('RESUMEN EJECUTIVO', BLUE);

  const SW = (CW - 10) / 3;
  [
    { n: data.riskCount,     label: 'Riesgos detectados', c: RED,   bg: REDBG   },
    { n: data.positiveCount, label: 'Aspectos positivos', c: GREEN, bg: GREENBG },
    { n: data.missingCount,  label: 'Elementos ausentes', c: AMBER, bg: AMBERBG },
  ].forEach((s, i) => {
    const sx = M + i * (SW + 5);
    fill(s.bg);
    pdf.roundedRect(sx, y, SW, 26, 3, 3, 'F');
    fill(s.c);
    pdf.roundedRect(sx, y, 4, 26, 2, 2, 'F');
    fnt('bold', 20);
    clr(s.c);
    pdf.text(String(s.n), sx + SW / 2 + 2, y + 15, { align: 'center' });
    fnt('normal', 8);
    clr(TMUTED);
    pdf.text(s.label, sx + SW / 2 + 2, y + 22, { align: 'center' });
  });
  y += 33;

  y += 4;

  // ══════════════════════════════════════════════════════════════════
  // HALLAZGOS
  // ══════════════════════════════════════════════════════════════════

  if (data.riskFindings.length > 0) {
    heading('RIESGOS DETECTADOS', RED);
    data.riskFindings.forEach((r, i) => listItem(i, r.title));
    y += 6;
  }

  if (data.missingElements.length > 0) {
    heading('ELEMENTOS AUSENTES', AMBER);
    data.missingElements.forEach((e, i) => listItem(i, e.title));
    y += 6;
  }

  if (data.positiveFindings.length > 0) {
    heading('ASPECTOS POSITIVOS', GREEN);
    data.positiveFindings.forEach((p, i) => listItem(i, p.title));
    y += 6;
  }

  if (data.negativeFindings && data.negativeFindings.length > 0) {
    heading('ASPECTOS NEGATIVOS', ORANGE);
    data.negativeFindings.forEach((p, i) => listItem(i, p.title));
    y += 6;
  }

  // ══════════════════════════════════════════════════════════════════
  // ANÁLISIS DE CLÁUSULAS
  // ══════════════════════════════════════════════════════════════════

  if (data.clauses.length > 0) {
    y = newPage();
    heading('ANÁLISIS DE CLÁUSULAS', BLUE);

    data.clauses.forEach((clause) => {
      const titleLines = wrap(`Cláusula ${clause.number}: ${clause.title}`, CW - 12);
      const barH = titleLines.length * 6.5 + 11;
      checkSpace(barH + 16);

      fill(LGRAY);
      pdf.roundedRect(M, y, CW, barH, 2, 2, 'F');
      fill(BLUE);
      pdf.roundedRect(M, y, 4, barH, 2, 2, 'F');
      fnt('bold', 11);
      clr(TMAIN);
      let ty = y + 8;
      titleLines.forEach(l => { pdf.text(l, M + 9, ty); ty += 6.5; });
      y += barH + 5;

      if (clause.technicalText) {
        fnt('italic', 9);
        clr(TMUTED);
        wrap(clause.technicalText, CW).forEach(l => { checkSpace(5); pdf.text(l, M, y); y += 5; });
        y += 3;
      }

      if (clause.plainLanguage) {
        checkSpace(14);
        fnt('bold', 9.5);
        clr(TMAIN);
        pdf.text('Explicación:', M, y);
        y += 6;
        fnt('normal', 9.5);
        clr(TMUTED);
        wrap(clause.plainLanguage, CW).forEach(l => { checkSpace(5); pdf.text(l, M, y); y += 5; });
        y += 4;
      }

      if (clause.category === 'risk' && clause.recommendations) {
        const recLines = wrap(clause.recommendations, CW - 18);
        const rh = recLines.length * 5 + 20;
        checkSpace(rh + 5);
        fill(AMBERBG);
        pdf.roundedRect(M, y, CW, rh, 2, 2, 'F');
        stroke(AMBER);
        pdf.setLineWidth(0.4);
        pdf.roundedRect(M, y, CW, rh, 2, 2, 'S');
        fill(AMBER);
        pdf.roundedRect(M, y, 4, rh, 2, 2, 'F');
        fnt('bold', 9);
        clr(AMBER);
        pdf.text('Recomendaciones Legales', M + 9, y + 9);
        fnt('normal', 9);
        clr(TMAIN);
        let ry = y + 15;
        recLines.forEach(l => { pdf.text(l, M + 9, ry); ry += 5; });
        y += rh + 7;
      }

      y += 8;
    });
  }

  // ══════════════════════════════════════════════════════════════════
  // RELACIONES ENTRE CLÁUSULAS
  // ══════════════════════════════════════════════════════════════════

  if (data.relations.length > 0) {
    y = newPage();
    heading('RELACIONES ENTRE CLÁUSULAS', BLUE);

    const relMap: Record<string, { label: string; color: RGB; bg: RGB }> = {
      contradiccion:                 { label: 'CONTRADICCIÓN',   color: RED,    bg: REDBG   },
      dependencia:                   { label: 'DEPENDENCIA',     color: BLUE,   bg: BLIGHT  },
      duplicidad:                    { label: 'DUPLICIDAD',      color: TMUTED, bg: LGRAY   },
      referencia_a_clausula_ausente: { label: 'REF. AUSENTE',    color: AMBER,  bg: AMBERBG },
    };

    data.relations.forEach(rel => {
      const rt = relMap[rel.type] ?? { label: rel.type.toUpperCase(), color: TMUTED, bg: LGRAY };
      const descLines = wrap(rel.description, CW - 18);
      const bh = descLines.length * 5 + 30;
      checkSpace(bh + 6);

      fill(rt.bg);
      pdf.roundedRect(M, y, CW, bh, 3, 3, 'F');
      fill(rt.color);
      pdf.roundedRect(M, y, 4, bh, 2, 2, 'F');

      fill(rt.color);
      pdf.roundedRect(M + 9, y + 6, 46, 8, 2, 2, 'F');
      fnt('bold', 7.5);
      clr(WHITE);
      pdf.text(rt.label, M + 32, y + 11.5, { align: 'center' });

      fnt('bold', 9.5);
      clr(TMAIN);
      const refs = rel.toClauseId
        ? `Cláusula ${rel.fromClauseId}  →  Cláusula ${rel.toClauseId}`
        : `Cláusula ${rel.fromClauseId}`;
      pdf.text(refs, M + 62, y + 11.5);

      fnt('normal', 9);
      clr(TMUTED);
      let ry = y + 22;
      descLines.forEach(l => { pdf.text(l, M + 9, ry); ry += 5; });

      y += bh + 7;
    });
  }

  // ══════════════════════════════════════════════════════════════════
  // PIE DE PÁGINA EN PÁGINAS INTERIORES (omite portada = página 1)
  // ══════════════════════════════════════════════════════════════════

  const total   = pdf.getNumberOfPages();
  const genDate = formatDate(new Date().toISOString(), data.language ?? 'es');

  for (let i = 2; i <= total; i++) {
    pdf.setPage(i);
    stroke(BORDER);
    pdf.setLineWidth(0.3);
    pdf.line(M, H - 13, W - M, H - 13);
    fnt('normal', 7);
    clr(TMUTED);
    pdf.text('ContratIA', M, H - 8);
    pdf.text(`Página ${i - 1} de ${total - 1}`, W / 2, H - 8, { align: 'center' });
    pdf.text(`Generado: ${genDate}`, W - M, H - 8, { align: 'right' });
  }

  pdf.save(`analisis_${data.filename.replace(/\.[^/.]+$/, '')}.pdf`);
}
