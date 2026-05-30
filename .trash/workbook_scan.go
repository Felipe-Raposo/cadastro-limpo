package main

import (
	"fmt"
	"io"
	"unicode/utf8"
)

// scanOpts agrupa opções de uma varredura de planilha (evita lista longa de parâmetros).
type scanOpts struct {
	MaxRows       int
	MaxCols       int
	Verbose       bool
	IgnoreAccents bool
	Log           io.Writer
}

// columnName converte índice de coluna (0 = A) para notação Excel (A, B, …, Z, AA, …).
func columnName(col int) string {
	name := make([]byte, 0, 8)
	for col >= 0 {
		name = append([]byte{byte('A' + col%26)}, name...)
		col = col/26 - 1
	}
	return string(name)
}

// cellRef monta a referência da célula (ex.: A1) a partir de linha e coluna base zero.
func cellRef(row, col int) string {
	return fmt.Sprintf("%s%d", columnName(col), row+1)
}

// scanSheet percorre uma planilha, atualiza estatísticas e devolve achados por célula.
func scanSheet(file, sheet string, rows [][]string, opts scanOpts, stats *ScanStats) []CellFinding {
	var out []CellFinding
	rowLimit := len(rows)
	if opts.MaxRows > 0 && opts.MaxRows < rowLimit {
		rowLimit = opts.MaxRows
	}
	stats.RowsScanned += rowLimit

	maxColThis := 0
	for ri := 0; ri < rowLimit; ri++ {
		row := rows[ri]
		colLimit := len(row)
		if opts.MaxCols > 0 && opts.MaxCols < colLimit {
			colLimit = opts.MaxCols
		}
		if colLimit > maxColThis {
			maxColThis = colLimit
		}
		for ci := 0; ci < colLimit; ci++ {
			val := row[ci]
			if val == "" {
				continue
			}
			stats.CharsScanned += int64(utf8.RuneCountInString(val))
			stats.NonEmptyCells++

			issues := ScanRunes(val, opts.IgnoreAccents)
			stats.InvalidErrors += countSevereIssueOccurrences(issues)

			if len(issues) == 0 {
				continue
			}
			out = append(out, CellFinding{
				File:    file,
				Sheet:   sheet,
				Cell:    cellRef(ri, ci),
				Snippet: truncateRunes(val, snippetRunesMax),
				Issues:  issues,
			})
		}
	}
	if maxColThis > stats.MaxColumns {
		stats.MaxColumns = maxColThis
	}
	vlog(opts.Verbose, opts.Log, "  Linhas consideradas nesta planilha (após -max-rows): %d\n", rowLimit)
	vlog(opts.Verbose, opts.Log, "  Largura máxima de colunas nesta planilha: %d\n", maxColThis)
	return out
}
