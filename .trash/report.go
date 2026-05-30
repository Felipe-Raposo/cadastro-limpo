package main

import (
	"encoding/json"
	"fmt"
	"io"
)

// truncateRunes limita s a no máximo max runas, acrescentando reticências se truncar.
func truncateRunes(s string, max int) string {
	if max <= 0 {
		return ""
	}
	n := 0
	for i := range s {
		if n == max {
			return s[:i] + "…"
		}
		n++
	}
	return s
}

// countCellsWithSeverityErrors conta células que contêm pelo menos um achado grave (inválido ou reservado).
func countCellsWithSeverityErrors(findings []CellFinding) int {
	n := 0
	for _, f := range findings {
		if findingHasSevereIssue(f) {
			n++
		}
	}
	return n
}

// collectSevereCodepoints reúne pontos de código únicos entre achados graves.
func collectSevereCodepoints(findings []CellFinding) []string {
	seen := make(map[string]struct{})
	var out []string
	for _, f := range findings {
		for _, iss := range f.Issues {
			if !issueIsSevere(iss) {
				continue
			}
			if _, ok := seen[iss.Codepoint]; ok {
				continue
			}
			seen[iss.Codepoint] = struct{}{}
			out = append(out, iss.Codepoint)
		}
	}
	return out
}

// printTextReport imprime no console o resumo, a lista de codepoints problemáticos e o detalhe por célula.
func printTextReport(w io.Writer, findings []CellFinding) {
	if len(findings) == 0 {
		fmt.Fprintln(w, msgReportClean)
		return
	}

	fmt.Fprintln(w, msgReportAttention)
	fmt.Fprintln(w)

	sevCells := countCellsWithSeverityErrors(findings)
	if sevCells > 0 {
		fmt.Fprintf(w, msgReportSevereFmt, sevCells)
		cps := collectSevereCodepoints(findings)
		fmt.Fprintln(w, msgReportCodeList)
		for _, cp := range cps {
			fmt.Fprintf(w, "  - %s\n", cp)
		}
		fmt.Fprintln(w)
	} else {
		fmt.Fprintln(w, msgReportOnlyWarn)
		fmt.Fprintln(w)
	}

	fmt.Fprintln(w, msgReportDetails)
	printFindingDetails(w, findings)
}

// printFindingDetails emite cada célula com problema e os achados por runa.
func printFindingDetails(w io.Writer, findings []CellFinding) {
	for _, f := range findings {
		fmt.Fprintf(w, "%s | %s | %s\n", f.Sheet, f.Cell, f.Snippet)
		for _, iss := range f.Issues {
			fmt.Fprintf(w, "  %s %s (%s)\n", iss.Kind, iss.Codepoint, string(iss.Rune))
		}
		fmt.Fprintln(w)
	}
}

// printFindingsJSON serializa os achados em JSON indentado.
func printFindingsJSON(w io.Writer, findings []CellFinding) error {
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	return enc.Encode(findings)
}

// exitCode define o código de saída do processo (exitOK, exitSevere ou exitWarning).
func exitCode(findings []CellFinding) int {
	for _, f := range findings {
		if findingHasSevereIssue(f) {
			return exitSevere
		}
	}
	if len(findings) > 0 {
		return exitWarning
	}
	return exitOK
}
