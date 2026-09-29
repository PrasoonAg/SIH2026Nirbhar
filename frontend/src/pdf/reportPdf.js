import { jsPDF } from 'jspdf'

function pct(num, den) {
  if (!den) return 'n/a'
  return `${((num / den) * 100).toFixed(1)}%`
}

export function downloadReportPdf(report) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' })
  const W = 595.28
  let y = 48
  const write = (t, size = 10, color = [15, 23, 42]) => {
    doc.setFont('courier', 'normal')
    doc.setFontSize(size)
    doc.setTextColor(...color)
    const wrapped = doc.splitTextToSize(String(t ?? ''), W - 80)
    wrapped.forEach(row => {
      if (y > 780) {
        doc.addPage()
        y = 48
      }
      doc.text(row, 40, y)
      y += size + 4
    })
  }

  doc.setFillColor(15, 23, 42)
  doc.rect(0, 0, W, 36, 'F')
  doc.setTextColor(226, 232, 240)
  doc.setFontSize(12)
  doc.setFont('helvetica', 'bold')
  doc.text('PRAMANA — Device Audit Report', 40, 24)

  y = 56
  write(`${report.device_id}  ·  ${report.site}  ·  ${report.vendor_id}`, 13)
  write(`Timestamp: ${report.audited_at}`)
  write(`Profile commit: ${report.profile_commit}`)
  write(`Gate-config hash: ${report.gate_config_hash}`)
  write(`Tool: ${report.tool_version}`)
  write(`ReportData SHA-256: ${report.report_data_sha256}`)
  y += 6
  write(`Verified ${pct(report.score.verified_numerator, report.score.verified_denominator)}  (${report.score.verified_numerator}/${report.score.verified_denominator})`, 12)
  write(`Provisional-Inclusive ${pct(report.score.provisional_inclusive_numerator, report.score.provisional_inclusive_denominator)}  (${report.score.provisional_inclusive_numerator}/${report.score.provisional_inclusive_denominator})`, 12)
  write(`Provisional dependence ${pct(report.score.provisional_dependence_numerator, report.score.provisional_inclusive_denominator)}`, 11)
  y += 8
  write('Findings', 13)
  ;(report.findings || []).forEach(f => {
    const blast = f.blast_radius_flag ? ` BLAST-RADIUS${f.blast_note ? ' — ' + f.blast_note : ''}` : ''
    write(`${f.check_id}  ${String(f.status).toUpperCase()}  ${String(f.trust || '').toUpperCase()}${blast}`)
  })
  y += 8
  write('Appendix A — Evidence for every Provisional mapping used', 13)
  if (!report.appendix_a?.length) {
    write('No Provisional mappings used in this report.')
  } else {
    report.appendix_a.forEach(a => {
      write(`${a.mapping_id}  ${a.setting_id}  cosine ${a.cosine}  gate ${a.gate_outcome}`)
    })
  }
  y += 8
  write('Appendix B — Self-audit summary + residual risk (INV-15)', 13)
  write(`Seed ${report.selfaudit_seed}  Corpus ${report.corpus_sha256}`)
  write(report.residual_risk_line)
  write(`Measured rate: ${report.residual_risk_rate}`)

  doc.save(`pramana-${report.device_id}.pdf`)
}
