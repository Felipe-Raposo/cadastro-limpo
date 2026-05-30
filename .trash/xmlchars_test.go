package main

import (
	"testing"
)

func TestIsXMLChar(t *testing.T) {
	cases := []struct {
		r    rune
		want bool
	}{
		{'\t', true},
		{'\n', true},
		{'\r', true},
		{' ', true},
		{'á', true},
		{'\x01', false},
		{'\x0B', false},
		{0xFFFE, false},
		{0xFFFF, false},
	}
	for _, tc := range cases {
		if got := IsXMLChar(tc.r); got != tc.want {
			t.Errorf("IsXMLChar(%q) = %v, want %v", tc.r, got, tc.want)
		}
	}
}

func TestScanRunes_invalidAndSuspicious(t *testing.T) {
	s := "ok\x01" + string('\u200B') + "fim"
	issues := ScanRunes(s, false)
	if len(issues) < 2 {
		t.Fatalf("want at least invalid + ZWSP, got %d issues", len(issues))
	}
	if issues[0].Kind != IssueInvalidXML {
		t.Errorf("first issue want invalid XML, got %s", issues[0].Kind)
	}
	var hasSusp bool
	for _, i := range issues {
		if i.Kind == IssueSuspicious && i.Rune == '\u200B' {
			hasSusp = true
		}
	}
	if !hasSusp {
		t.Error("expected suspicious zero-width space")
	}
}

func TestScanRunes_portugueseAccents(t *testing.T) {
	cases := []struct {
		word string
		want int
	}{
		{"café", 1},
		{"atenção", 2},
		{"almoço", 1},
	}
	for _, tc := range cases {
		var n int
		for _, iss := range ScanRunes(tc.word, false) {
			if iss.Kind == IssueSuspicious {
				n++
			}
		}
		if n != tc.want {
			t.Errorf("%q: want %d suspicious (accented Latin), got %d", tc.word, tc.want, n)
		}
	}
}

func TestScanRunes_ignoreAccents(t *testing.T) {
	issues := ScanRunes("café", true)
	if len(issues) != 0 {
		t.Errorf("with ignore-accents, café should have no issues, got %+v", issues)
	}
}

func TestScanRunes_unicodeOutsidePrintableASCII(t *testing.T) {
	issues := ScanRunes("€", false)
	if len(issues) != 1 || issues[0].Kind != IssueUnicodeOutsidePrintASCII {
		t.Fatalf("want 1 unicode_outside_ascii_32_126 for euro, got %+v", issues)
	}
}

func TestScanRunes_asciiOutsidePrintableRange(t *testing.T) {
	// Tab (9), LF (10) e DEL (127) são ASCII fora de 32–126.
	issues := ScanRunes("a\tb\nc"+string(rune(127)), false)
	var ascii int
	for _, i := range issues {
		if i.Kind == IssueASCIIOutOfRange {
			ascii++
		}
	}
	if ascii != 3 {
		t.Errorf("want 3 ascii_out_of_range issues, got %d", ascii)
	}
}

func TestScanRunes_reservedAlways(t *testing.T) {
	issues := ScanRunes(`a & b < c > "x" 'y'`, false)
	var reserved int
	for _, i := range issues {
		if i.Kind == IssueXMLReserved {
			reserved++
		}
	}
	if reserved != 5 {
		t.Errorf("want 5 xml_reserved_char issues (& < > \" \" ), got %d", reserved)
	}
}

func TestIsSeverityError(t *testing.T) {
	if !IsSeverityError(IssueInvalidXML) || !IsSeverityError(IssueASCIIOutOfRange) || !IsSeverityError(IssueUnicodeOutsidePrintASCII) || !IsSeverityError(IssueXMLReserved) {
		t.Error("invalid, ascii range, unicode outside printable and reserved should be severity")
	}
	if IsSeverityError(IssueSuspicious) {
		t.Error("suspicious should not be severity")
	}
}

func TestTruncateRunes(t *testing.T) {
	if got := truncateRunes("abcdefghij", 5); got != "abcde…" {
		t.Errorf("got %q", got)
	}
	if got := truncateRunes("short", snippetRunesMax); got != "short" {
		t.Errorf("got %q", got)
	}
}

func TestColumnName(t *testing.T) {
	tests := []struct {
		col  int
		want string
	}{
		{0, "A"},
		{25, "Z"},
		{26, "AA"},
		{27, "AB"},
	}
	for _, tt := range tests {
		if got := columnName(tt.col); got != tt.want {
			t.Errorf("columnName(%d) = %q, want %q", tt.col, got, tt.want)
		}
	}
}

func TestExitCode(t *testing.T) {
	if c := exitCode(nil); c != exitOK {
		t.Errorf("empty: %d", c)
	}
	if c := exitCode([]CellFinding{{Issues: []RuneIssue{{Kind: IssueSuspicious}}}}); c != exitWarning {
		t.Errorf("warnings only: %d", c)
	}
	if c := exitCode([]CellFinding{{Issues: []RuneIssue{{Kind: IssueInvalidXML}}}}); c != exitSevere {
		t.Errorf("invalid: %d", c)
	}
	if c := exitCode([]CellFinding{{Issues: []RuneIssue{{Kind: IssueASCIIOutOfRange}}}}); c != exitSevere {
		t.Errorf("ascii out of range: %d", c)
	}
	if c := exitCode([]CellFinding{{Issues: []RuneIssue{{Kind: IssueUnicodeOutsidePrintASCII}}}}); c != exitSevere {
		t.Errorf("unicode outside printable ascii: %d", c)
	}
	if c := exitCode([]CellFinding{{Issues: []RuneIssue{{Kind: IssueXMLReserved}}}}); c != exitSevere {
		t.Errorf("reserved: %d", c)
	}
}

func TestFindingHasSevereIssue(t *testing.T) {
	if findingHasSevereIssue(CellFinding{Issues: []RuneIssue{{Kind: IssueSuspicious}}}) {
		t.Fatal("suspicious only should not be severe")
	}
	if !findingHasSevereIssue(CellFinding{Issues: []RuneIssue{{Kind: IssueInvalidXML}}}) {
		t.Fatal("invalid should be severe")
	}
	if !findingHasSevereIssue(CellFinding{Issues: []RuneIssue{{Kind: IssueASCIIOutOfRange}}}) {
		t.Fatal("ascii out of range should be severe")
	}
	if !findingHasSevereIssue(CellFinding{Issues: []RuneIssue{{Kind: IssueUnicodeOutsidePrintASCII}}}) {
		t.Fatal("unicode outside printable ascii should be severe")
	}
	if countSevereIssueOccurrences([]RuneIssue{{Kind: IssueXMLReserved}, {Kind: IssueSuspicious}}) != 1 {
		t.Fatal("count severe")
	}
}
