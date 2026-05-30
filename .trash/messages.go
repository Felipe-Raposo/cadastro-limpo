package main

// Mensagens de interface (relatório, erros de CLI, resumo). Texto em português (Brasil).

const (
	msgUsage = `chartool — Verifica caracteres problemáticos em planilhas Excel para uso em XML (NF-e).

Copyright (c) 2026 Felipe Raposo <feliperaposo@gmail.com>

O utilitário inspeciona o conteúdo textual das células. Ele não substitui o validador da SEFAZ;
foco: sanidade dos dados (XML 1.0, ASCII 32–126, letras latinas acentuadas, caracteres reservados & < > ", invisíveis comuns).

Uso: chartool [flags] arquivo.xlsx

Use -ignore-accents para não tratar letras latinas acentuadas (é, ç, ã, …) como suspeitas.

Flags:
`

	msgErrFileInaccessible = "erro: arquivo inacessível: %v\n"
	msgErrOpenExcel        = "erro ao abrir Excel: %v\n"
	msgErrSheetNotFound = "erro: planilha não encontrada: %q"
	msgErrReadSheet        = "erro ao ler planilha %q: %v"
	msgErrEmitJSON         = "erro ao emitir JSON: %v\n"

	msgReportClean     = "Arquivo limpo: não foram encontrados caracteres problemáticos nas células analisadas."
	msgReportAttention = "Atenção: foram encontrados caracteres problemáticos (o arquivo não está limpo)."
	msgReportSevereFmt = "Caracteres inválidos para XML 1.0, fora da faixa ASCII imprimível 32–126 (incl. Unicode não permitido), ou reservados (& < > \") em %d célula(s).\n"
	msgReportCodeList  = "Lista de codepoints encontrados (únicos):"
	msgReportOnlyWarn  = "Nenhum caractere inválido, ASCII fora da faixa ou reservado; os achados abaixo são apenas avisos (caracteres invisíveis/suspeitos)."
	msgReportDetails   = "Detalhes por célula (planilha | célula | trecho do valor):"

	msgSummaryTitle          = "--- Resumo da análise ---"
	msgSummarySheets         = "Planilhas processadas: %d\n"
	msgSummaryRows           = "Linhas analisadas: %d\n"
	msgSummaryCols           = "Colunas (largura máxima observada): %d\n"
	msgSummaryChars          = "Caracteres (runas) analisados: %d\n"
	msgSummaryNonEmpty       = "Células não vazias analisadas: %d\n"
	msgSummaryErrors         = "Erros (inválidos XML 1.0, fora ASCII 32–126, Unicode não permitido, ou reservados & < > \"): %d\n"
	msgProcessingTime        = "\nTempo de processamento: %v\n"
)
