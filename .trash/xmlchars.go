package main

import (
	"fmt"
	"unicode"
)

// IsXMLChar indica se r é permitido no conteúdo XML 1.0 (produção Char).
// Ver: https://www.w3.org/TR/xml/#char
func IsXMLChar(r rune) bool {
	switch {
	case r == 0x9 || r == 0xA || r == 0xD:
		return true
	case r >= 0x20 && r <= 0xD7FF:
		return true
	case r >= 0xE000 && r <= 0xFFFD:
		return true
	case r >= 0x10000 && r <= 0x10FFFF:
		return true
	default:
		return false
	}
}

func formatCodepoint(r rune) string {
	if r <= 0xFFFF {
		return fmt.Sprintf("U+%04X", r)
	}
	return fmt.Sprintf("U+%X", r)
}

// isASCIIOutsidePrintableRange reporta ASCII (U+0000–U+007F) fora da faixa 32–126 (inclusive).
// Espaço (32) até tilde (~, 126) são aceitos; tab, LF, CR e DEL, entre outros, são rejeitados.
func isASCIIOutsidePrintableRange(r rune) bool {
	if r > 0x7F {
		return false
	}
	return r < 32 || r > 126
}

// isLatinLetterNonASCII indica letras do alfabeto latino com codepoint acima de 127
// (acentuadas, ç, Ç, etc.), tratadas como suspeitas para integrações que esperam ASCII.
func isLatinLetterNonASCII(r rune) bool {
	if r <= 127 {
		return false
	}
	return unicode.IsLetter(r) && unicode.Is(unicode.Latin, r)
}

// ScanRunes retorna todos os achados encontrados em s, na ordem de leitura.
// Só são aceitos sem achado os caracteres na faixa ASCII imprimível 32–126 (exceto reservados XML).
// Caracteres reservados em XML (& < > ") são sempre reportados como IssueXMLReserved.
// ASCII (U+00–U+7F) fora de 32–126 é IssueASCIIOutOfRange.
// Letras latinas não ASCII (ç, acentos) são IssueSuspicious, salvo com -ignore-accents.
// Unicode fora da faixa permitida e que não seja suspeito acima é IssueUnicodeOutsidePrintASCII.
func ScanRunes(s string, ignoreAccents bool) []RuneIssue {
	var out []RuneIssue
	for _, r := range s {
		if !IsXMLChar(r) {
			out = append(out, RuneIssue{Rune: r, Codepoint: formatCodepoint(r), Kind: IssueInvalidXML})
			continue
		}
		if isASCIIOutsidePrintableRange(r) {
			out = append(out, RuneIssue{Rune: r, Codepoint: formatCodepoint(r), Kind: IssueASCIIOutOfRange})
			continue
		}
		if isXMLReserved(r) {
			out = append(out, RuneIssue{Rune: r, Codepoint: formatCodepoint(r), Kind: IssueXMLReserved})
			continue
		}
		if isSuspicious(r, ignoreAccents) {
			out = append(out, RuneIssue{Rune: r, Codepoint: formatCodepoint(r), Kind: IssueSuspicious})
			continue
		}
		if r > 127 {
			if ignoreAccents && isLatinLetterNonASCII(r) {
				continue
			}
			out = append(out, RuneIssue{Rune: r, Codepoint: formatCodepoint(r), Kind: IssueUnicodeOutsidePrintASCII})
			continue
		}
	}
	return out
}

func isXMLReserved(r rune) bool {
	switch r {
	case '&', '<', '>', '"':
		return true
	default:
		return false
	}
}

func isSuspicious(r rune, ignoreAccents bool) bool {
	if !ignoreAccents && isLatinLetterNonASCII(r) {
		return true
	}
	switch r {
	case '\u00A0', '\u1680', '\u2000', '\u2001', '\u2002', '\u2003', '\u2004',
		'\u2005', '\u2006', '\u2007', '\u2008', '\u2009', '\u200A', '\u200B',
		'\u200C', '\u200D', '\u200E', '\u200F', '\u2028', '\u2029', '\u202F',
		'\u205F', '\u2060', '\u3000', '\uFEFF':
		return true
	default:
		return false
	}
}

// IsSeverityError indica tipos de achado que invalidam o arquivo (código de saída exitSevere).
func IsSeverityError(k IssueKind) bool {
	switch k {
	case IssueInvalidXML, IssueASCIIOutOfRange, IssueUnicodeOutsidePrintASCII, IssueXMLReserved:
		return true
	default:
		return false
	}
}
