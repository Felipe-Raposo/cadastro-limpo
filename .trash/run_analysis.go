package main

import (
	"fmt"
	"io"
	"path/filepath"

	"github.com/xuri/excelize/v2"
)

// runAnalysis percorre o workbook, aplica filtro de planilha e limites, e acumula achados e estatísticas.
func runAnalysis(f *excelize.File, path string, sheetFilter string, maxRows, maxCols int, verbose bool, ignoreAccents bool, logW io.Writer) (findings []CellFinding, stats ScanStats, absPath string, err error) {
	absPath, _ = filepath.Abs(path)

	sheets := f.GetSheetList()

	vlog(verbose, logW, "[1/5] Caminho absoluto: %s\n", absPath)
	vlog(verbose, logW, "[2/5] Workbook aberto com sucesso.\n")
	vlog(verbose, logW, "[3/5] Planilhas no arquivo: %d — %v\n", len(sheets), sheets)

	if sheetFilter != "" {
		found := false
		for _, name := range sheets {
			if name == sheetFilter {
				found = true
				break
			}
		}
		if !found {
			return nil, stats, absPath, fmt.Errorf(msgErrSheetNotFound, sheetFilter)
		}
		vlog(verbose, logW, "Filtro ativo: somente a planilha %q.\n", sheetFilter)
	}

	vlog(verbose, logW, "[4/5] Iniciando leitura e análise das células...\n")

	opts := scanOpts{MaxRows: maxRows, MaxCols: maxCols, Verbose: verbose, IgnoreAccents: ignoreAccents, Log: logW}

	for _, sh := range sheets {
		if sheetFilter != "" && sh != sheetFilter {
			continue
		}
		stats.SheetsProcessed++
		vlog(verbose, logW, "\n--- Planilha %q ---\n", sh)
		rows, errRows := f.GetRows(sh)
		if errRows != nil {
			return nil, stats, absPath, fmt.Errorf(msgErrReadSheet, sh, errRows)
		}
		vlog(verbose, logW, "  GetRows retornou %d linha(s).\n", len(rows))
		findings = append(findings, scanSheet(absPath, sh, rows, opts, &stats)...)
	}

	vlog(verbose, logW, "\n[5/5] Varredura concluída.\n")
	return findings, stats, absPath, nil
}
