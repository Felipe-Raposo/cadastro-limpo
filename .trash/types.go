package main

// IssueKind classifica o tipo de achado na análise.
type IssueKind string

const (
	IssueInvalidXML               IssueKind = "invalid_xml_1.0"
	IssueASCIIOutOfRange          IssueKind = "ascii_out_of_range"
	IssueUnicodeOutsidePrintASCII IssueKind = "unicode_outside_ascii_32_126"
	IssueXMLReserved              IssueKind = "xml_reserved_char"
	IssueSuspicious               IssueKind = "suspicious_invisible_or_special"
)

// RuneIssue descreve uma runa problemática dentro de uma string.
type RuneIssue struct {
	Rune      rune
	Codepoint string // representação U+XXXX do ponto de código
	Kind      IssueKind
}

// CellFinding representa uma célula em que foi detectado pelo menos um achado.
type CellFinding struct {
	File    string      `json:"file"`
	Sheet   string      `json:"sheet"`
	Cell    string      `json:"cell"`
	Snippet string      `json:"snippet"`
	Issues  []RuneIssue `json:"issues"`
}

// issueIsSevere indica se o achado conta como erro (código de saída exitSevere).
func issueIsSevere(iss RuneIssue) bool {
	return IsSeverityError(iss.Kind)
}

// findingHasSevereIssue indica se a célula tem pelo menos um achado grave.
func findingHasSevereIssue(f CellFinding) bool {
	for _, iss := range f.Issues {
		if issueIsSevere(iss) {
			return true
		}
	}
	return false
}

// countSevereIssueOccurrences conta ocorrências de achados graves na lista (por runa).
func countSevereIssueOccurrences(issues []RuneIssue) int {
	n := 0
	for _, iss := range issues {
		if issueIsSevere(iss) {
			n++
		}
	}
	return n
}
