package main

import (
	"fmt"
	"io"
)

// ScanStats acumula métricas da varredura em todas as planilhas processadas.
type ScanStats struct {
	SheetsProcessed int
	RowsScanned     int
	MaxColumns      int
	CharsScanned    int64 // soma de runas em células não vazias analisadas
	NonEmptyCells   int
	InvalidErrors   int // ocorrências graves: inválido XML 1.0, ASCII fora de 32–126, Unicode fora da faixa, ou reservado (&, <, >, ")
}

// printScanSummary imprime o bloco de totais ao usar a flag -summarize.
func printScanSummary(w io.Writer, st ScanStats) {
	fmt.Fprintln(w)
	fmt.Fprintln(w, msgSummaryTitle)
	fmt.Fprintf(w, msgSummarySheets, st.SheetsProcessed)
	fmt.Fprintf(w, msgSummaryRows, st.RowsScanned)
	fmt.Fprintf(w, msgSummaryCols, st.MaxColumns)
	fmt.Fprintf(w, msgSummaryChars, st.CharsScanned)
	fmt.Fprintf(w, msgSummaryNonEmpty, st.NonEmptyCells)
	fmt.Fprintf(w, msgSummaryErrors, st.InvalidErrors)
}

// vlog escreve em w apenas se verbose for true (útil para stderr com -verbose).
func vlog(verbose bool, w io.Writer, format string, a ...any) {
	if !verbose || w == nil {
		return
	}
	fmt.Fprintf(w, format, a...)
}
