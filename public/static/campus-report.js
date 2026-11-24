"use strict";

function createCampusReport(data, generatedAt) {
  const pageWidth = 595;
  const pageHeight = 842;
  const margin = 42;
  const ink = "0.13 0.15 0.22";
  const muted = "0.36 0.39 0.46";
  const blue = "0.14 0.28 0.85";
  const green = "0.14 0.52 0.40";
  const orange = "0.68 0.28 0.17";
  const pale = "0.94 0.95 0.98";
  const white = "1 1 1";
  const formatNumber = new Intl.NumberFormat("pt-BR");
  const drawing = [];

  function rectangle(x, top, width, height, color) {
    const roundedWidth = width.toFixed(2);
    if (roundedWidth === "0.00") return;
    drawing.push(`${color} rg ${x} ${pageHeight - top - height} ${roundedWidth} ${height} re f`);
  }

  function text(value, x, top, size, color = ink, bold = false) {
    // Os nomes dos blocos e textos em português cabem no subconjunto Latin-1 da fonte WinAnsi.
    const hex = Array.from(value.replace(/[^\x20-\x7e\xa0-\xff]/gu, "?"),
      character => character.charCodeAt(0).toString(16).padStart(2, "0")).join("");
    drawing.push(`BT ${color} rg /${bold ? "F2" : "F1"} ${size} Tf ${x} ${pageHeight - top} Td <${hex}> Tj ET`);
  }

  rectangle(0, 0, pageWidth, 158, "0.09 0.14 0.30");
  rectangle(0, 0, 7, 158, blue);
  text("RESOLVE CAMPUS", margin, 45, 11, white, true);
  text("Situação atual do campus", margin, 89, 30, white, true);
  text(`Gerado em ${generatedAt}`, margin, 120, 11, white);

  text("Resumo das ocorrências", margin, 199, 19, ink, true);
  const indicators = [
    ["Total de ocorrências", data.total, ink],
    ["Pendentes", data.pendentes, blue],
    ["Urgentes", data.urgentes, orange],
    ["Resolvidas", data.resolvidos, green],
  ];
  const cardWidth = 120;
  indicators.forEach(([label, count, color], index) => {
    const x = margin + index * (cardWidth + 10);
    const formattedCount = formatNumber.format(count);
    rectangle(x, 218, cardWidth, 74, pale);
    rectangle(x, 218, cardWidth, 3, color);
    text(label, x + 12, 242, 10, muted);
    text(formattedCount, x + 12, 273, Math.min(24, Math.floor(160 / formattedCount.length)), color, true);
  });
  text("As urgências fazem parte das ocorrências pendentes.", margin, 312, 10, muted);

  text("Ocorrências por bloco", margin, 366, 19, ink, true);
  rectangle(margin, 383, 9, 9, blue);
  text("Pendentes", margin + 15, 391, 10, muted);
  rectangle(133, 383, 9, 9, green);
  text("Resolvidas", 148, 391, 10, muted);

  const chartX = 201;
  const chartWidth = 215;
  const pendingX = 433;
  const resolvedX = 496;
  const chartTop = 430;
  const rowHeight = 53;
  const scale = Math.max(1, ...data.blocos.map(block => block.total));
  text("Pendentes", pendingX, chartTop - 8, 9, muted, true);
  text("Resolvidas", resolvedX, chartTop - 8, 9, muted, true);
  data.blocos.forEach((block, index) => {
    const top = chartTop + index * rowHeight;
    const resolved = block.total - block.pendentes;
    const pendingWidth = block.pendentes / scale * chartWidth;
    const resolvedWidth = resolved / scale * chartWidth;
    text(`Bloco ${block.bloco}`, margin, top + 15, 11, ink, true);
    text(block.nome, margin, top + 30, 10, muted);
    rectangle(chartX, top + 5, chartWidth, 15, pale);
    rectangle(chartX, top + 5, pendingWidth, 15, blue);
    rectangle(chartX + pendingWidth, top + 5, resolvedWidth, 15, green);
    text(formatNumber.format(block.pendentes), pendingX, top + 17, 10, ink, true);
    text(formatNumber.format(resolved), resolvedX, top + 17, 10, ink, true);
  });
  if (data.total === 0) {
    text("Nenhuma ocorrência registrada no campus.", margin, chartTop + data.blocos.length * rowHeight + 15, 11, muted);
  }

  // O documento contém apenas comandos ASCII, então o tamanho das strings equivale ao tamanho em bytes.
  const stream = drawing.join("\n") + "\n";
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}endstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const references = ["0000000000 65535 f \n"];
  objects.forEach((object, index) => {
    references.push(`${String(pdf.length).padStart(10, "0")} 00000 n \n`);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const start = pdf.length;
  pdf += `xref\n0 ${references.length}\n${references.join("")}trailer\n<< /Size ${references.length} /Root 1 0 R >>\nstartxref\n${start}\n%%EOF\n`;
  return new Blob([pdf], { type: "application/pdf" });
}
