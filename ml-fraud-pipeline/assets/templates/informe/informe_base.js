// Constructor base del informe en Word con docx-js (npm install docx). Uso:
//   PROYECTO_RAIZ=/ruta/al/proyecto node informe_base.js salida.docx
// Rellena las secciones con contenido cuyas cifras salgan de código ejecutado. Después: validar el .docx,
// exportar a PDF y REVISAR VISUALMENTE cada página (ver references/08-informe.md).
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, HeadingLevel, AlignmentType,
  LevelFormat, WidthType, ShadingType, BorderStyle, PageBreak, Header, Footer, PageNumber } = require("docx");

const SALIDA = process.argv[2] || "informe.docx";
const AZUL = "1F3864", AZUL2 = "2F5496", GRIS = "595959", ANCHO = 9360, FUENTE = "Calibri";

// ---------- utilidades ----------
function runs(texto, base = {}) {
  const partes = texto.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)/g).filter(Boolean);
  return partes.map((p) => {
    if (p.startsWith("**")) return new TextRun({ text: p.slice(2, -2), bold: true, ...base });
    if (p.startsWith("*") && p.endsWith("*") && p.length > 2) return new TextRun({ text: p.slice(1, -1), italics: true, ...base });
    if (p.startsWith("`")) return new TextRun({ text: p.slice(1, -1), font: "Consolas", ...base, size: (base.size || 21) - 2 });
    return new TextRun({ text: p, ...base });
  });
}
const p = (t, o = {}) => new Paragraph({ children: runs(t, o.run || {}), spacing: { after: o.after ?? 120, line: 276 }, alignment: o.align, indent: o.indent, keepNext: o.keepNext });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t })], pageBreakBefore: false });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t })] });
const h3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: t })] });
const bullets = (items, ref = "vinetas") => items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), spacing: { after: 60, line: 264 } }));
let nNum = 0; const refsNum = [];
const numerada = (items) => { const ref = "num" + (++nNum); refsNum.push(ref);
  return items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), spacing: { after: 60, line: 264 } })); };
const salto = () => new Paragraph({ children: [new PageBreak()] });
const nota = (t) => new Paragraph({
  children: runs(t, { size: 20 }), spacing: { before: 80, after: 160, line: 264 },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: AZUL2, space: 8 } },
  shading: { type: ShadingType.CLEAR, fill: "EEF3FA" }, indent: { left: 200, right: 100 },
});

const borde = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const bordes = { top: borde, bottom: borde, left: borde, right: borde };
function tabla(encabezados, filas, anchos, o = {}) {
  const suma = anchos.reduce((a, b) => a + b, 0);
  const celda = (txt, i, cab, fila) => new TableCell({
    width: { size: anchos[i], type: WidthType.DXA }, borders: bordes,
    shading: cab ? { type: ShadingType.CLEAR, fill: "DCE6F1" } : (o.resaltar && o.resaltar(fila) ? { type: ShadingType.CLEAR, fill: "FFF4D6" } : undefined),
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ alignment: (o.centrar || []).includes(i) ? AlignmentType.CENTER : AlignmentType.LEFT, spacing: { after: 0 },
      children: runs(String(txt), { size: o.tam || 18, bold: cab ? true : undefined }) })],
  });
  return new Table({
    width: { size: suma, type: WidthType.DXA }, columnWidths: anchos,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: encabezados.map((t, i) => celda(t, i, true)) }),
      ...filas.map((f) => new TableRow({ cantSplit: true, children: f.map((t, i) => celda(t, i, false, f)) })),
    ],
  });
}
function dimensionesPng(ruta) {
  const b = fs.readFileSync(ruta);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function fig(archivo, pie, anchoPx = 600) {
  const ruta = `${process.env.PROYECTO_RAIZ || "."}/reports/figuras/${archivo}`;
  const { w, h } = dimensionesPng(ruta);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: fs.readFileSync(ruta), transformation: { width: anchoPx, height: Math.round(anchoPx * h / w) },
        altText: { title: pie, description: pie, name: archivo } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: runs(pie, { size: 18, italics: true, color: GRIS }) }),
  ];
}

// ---------- contenido (ejemplo mínimo) ----------
const secciones = [
  h1("1. Resumen ejecutivo"),
  p("Aproximación al problema, resultado, hipótesis y estrategia de prevención. Solo cifras verificadas."),
  tabla(["Modelo", "PR-AUC (CV)", "PR-AUC (test)"], [["(modelo)", "0,000 ± 0,000", "0,000"]], [3000, 3180, 3180], { centrar: [1, 2] }),
  nota("Declara aquí lo que NO se verificó (simulaciones, supuestos)."),
];

const doc = new Document({
  styles: {
    default: { document: { run: { font: FUENTE, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 32, bold: true, color: AZUL }, paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0, keepNext: true } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, color: AZUL2 }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1, keepNext: true } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 22, bold: true, color: GRIS }, paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2, keepNext: true } },
    ],
  },
  numbering: { config: [
    { reference: "vinetas", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    ...refsNum.map((reference) => ({ reference, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] })),
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, right: 1440, bottom: 1200, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Página ", size: 16, color: GRIS }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GRIS })] })] }) },
    children: secciones,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(SALIDA, buf); console.log("docx escrito:", SALIDA); });
