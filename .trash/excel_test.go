package main

import (
	"path/filepath"
	"testing"

	"github.com/xuri/excelize/v2"
)

func TestScanSheet_fromXLSX(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "sample.xlsx")

	f := excelize.NewFile()
	if err := f.SetCellValue("Sheet1", "A1", "ok"); err != nil {
		t.Fatal(err)
	}
	// Espaço de largura zero: o Excel persiste; o caractere de controle 0x01 costuma ser removido.
	if err := f.SetCellValue("Sheet1", "B1", "x\u200By"); err != nil {
		t.Fatal(err)
	}
	if err := f.SaveAs(path); err != nil {
		t.Fatal(err)
	}
	_ = f.Close()

	f2, err := excelize.OpenFile(path)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = f2.Close() }()

	rows, err := f2.GetRows("Sheet1")
	if err != nil {
		t.Fatal(err)
	}
	var st ScanStats
	opts := scanOpts{Verbose: false, Log: nil}
	findings := scanSheet(path, "Sheet1", rows, opts, &st)
	if len(findings) != 1 {
		t.Fatalf("want 1 finding, got %d", len(findings))
	}
	if findings[0].Cell != "B1" {
		t.Errorf("cell: %s", findings[0].Cell)
	}
	if findings[0].Issues[0].Kind != IssueSuspicious {
		t.Errorf("kind: %s", findings[0].Issues[0].Kind)
	}
}
