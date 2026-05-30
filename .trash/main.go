package main

import (
	"flag"
	"fmt"
	"os"
	"time"

	"github.com/xuri/excelize/v2"
)

func main() {
	sheet := flag.String("sheet", "", "Nome da planilha; se vazio, processa todas")
	maxRows := flag.Int("max-rows", 0, "Máximo de linhas por planilha (0 = sem limite)")
	maxCols := flag.Int("max-cols", 0, "Máximo de colunas (0 = sem limite)")
	asJSON := flag.Bool("json", false, "Saída em JSON")
	verbose := flag.Bool("verbose", false, "Exibir cada etapa do processamento no console (stderr)")
	summarize := flag.Bool("summarize", false, "Ao final, exibir resumo: linhas, colunas, caracteres e erros")
	ignoreAccents := flag.Bool("ignore-accents", false, "Não marcar letras latinas acentuadas (é, ç, ã, …) como suspeitas")
	flag.Usage = func() {
		fmt.Fprint(os.Stderr, msgUsage)
		flag.PrintDefaults()
	}
	flag.Parse()

	args := flag.Args()
	if len(args) != 1 {
		flag.Usage()
		os.Exit(1)
	}
	path := args[0]
	if _, err := os.Stat(path); err != nil {
		fmt.Fprintf(os.Stderr, msgErrFileInaccessible, err)
		os.Exit(1)
	}

	f, err := excelize.OpenFile(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, msgErrOpenExcel, err)
		os.Exit(1)
	}
	defer func() { _ = f.Close() }()

	start := time.Now()

	logW := os.Stderr
	findings, stats, _, err := runAnalysis(f, path, *sheet, *maxRows, *maxCols, *verbose, *ignoreAccents, logW)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}

	if *asJSON {
		if err := printFindingsJSON(os.Stdout, findings); err != nil {
			fmt.Fprintf(os.Stderr, msgErrEmitJSON, err)
			os.Exit(1)
		}
	} else {
		printTextReport(os.Stdout, findings)
	}

	if *summarize {
		if *asJSON {
			printScanSummary(os.Stderr, stats)
		} else {
			printScanSummary(os.Stdout, stats)
		}
	}

	elapsed := time.Since(start)
	fmt.Fprintf(os.Stderr, msgProcessingTime, elapsed)

	code := exitCode(findings)
	os.Exit(code)
}
