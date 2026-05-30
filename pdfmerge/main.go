package main

import (
	"flag"
	"fmt"
	"os"
	"strings"

	"github.com/pdfcpu/pdfcpu/pkg/api"
)

const copyright = `pdfmerge - Junta dois ou mais arquivos PDF em um único arquivo
Copyright (c) 2025. Todos os direitos reservados.
Felipe Raposo <feliperaposo@gmail.com>

Uso: pdfmerge -o saida.pdf [--optimize] [--trim --pages SELECAO] arquivo1.pdf arquivo2.pdf [arquivo3.pdf ...]

Flags:
  -o string
    	Arquivo PDF de saída
  -optimize
    	Otimizar o PDF mesclado (reduz tamanho)
  -trim
    	Aplicar trim nas páginas selecionadas
  -pages string
    	Seleção de páginas para --trim (ex: 1-5, odd, even, 1,3,7)
  -help
    	Exibir esta ajuda
`

func printUsage() {
	fmt.Fprint(os.Stderr, copyright)
	fmt.Fprintln(os.Stderr, "Uso: pdfmerge -o saida.pdf [--optimize] [--trim --pages SELECAO] arquivo1.pdf arquivo2.pdf [arquivo3.pdf ...]")
	fmt.Fprintln(os.Stderr)
	flag.PrintDefaults()
}

func main() {
	output := flag.String("o", "", "Arquivo PDF de saída")
	optimize := flag.Bool("optimize", false, "Otimizar o PDF mesclado (reduz tamanho)")
	trim := flag.Bool("trim", false, "Aplicar trim nas páginas selecionadas")
	pages := flag.String("pages", "", "Seleção de páginas para --trim (ex: 1-5, odd, even, 1,3,7)")
	help := flag.Bool("help", false, "Exibir esta ajuda")
	flag.Usage = printUsage
	flag.Parse()

	args := flag.Args()
	if *help || (len(args) < 2 && *output == "") {
		printUsage()
		os.Exit(0)
	}

	if len(args) < 2 {
		fmt.Fprintln(os.Stderr, "Erro: Informe pelo menos dois arquivos PDF para mesclar.")
		os.Exit(1)
	}

	if *output == "" {
		fmt.Fprintln(os.Stderr, "Erro: Especifique o arquivo de saída com -o")
		os.Exit(1)
	}

	if *trim && *pages == "" {
		fmt.Fprintln(os.Stderr, "Erro: --trim requer --pages (ex: --pages 1-10 ou --pages odd)")
		os.Exit(1)
	}

	for _, f := range args {
		if _, err := os.Stat(f); os.IsNotExist(err) {
			fmt.Fprintf(os.Stderr, "Erro: Arquivo não encontrado: %s\n", f)
			os.Exit(1)
		}
		if !strings.HasSuffix(strings.ToLower(f), ".pdf") {
			fmt.Fprintf(os.Stderr, "Aviso: %s pode não ser um PDF válido.\n", f)
		}
	}

	if err := api.MergeCreateFile(args, *output, false, nil); err != nil {
		fmt.Fprintf(os.Stderr, "Erro ao mesclar PDFs: %v\n", err)
		os.Exit(1)
	}

	if *trim {
		selectedPages := strings.Split(*pages, ",")
		for i := range selectedPages {
			selectedPages[i] = strings.TrimSpace(selectedPages[i])
		}
		if err := api.TrimFile(*output, "", selectedPages, nil); err != nil {
			fmt.Fprintf(os.Stderr, "Erro ao aplicar trim: %v\n", err)
			os.Exit(1)
		}
	}

	if *optimize {
		if err := api.OptimizeFile(*output, "", nil); err != nil {
			fmt.Fprintf(os.Stderr, "Erro ao otimizar: %v\n", err)
			os.Exit(1)
		}
	}

	fmt.Printf("✓ PDFs mesclados com sucesso em: %s\n", *output)
}
