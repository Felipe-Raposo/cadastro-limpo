# PDF Merge

Ferramenta em Go para juntar dois ou mais arquivos PDF em um único arquivo.

## Compilação

```bash
cd pdfmerge
go build -o pdfmerge .
```

## Uso

```bash
./pdfmerge -o saida.pdf [--optimize] [--trim --pages SELECAO] arquivo1.pdf arquivo2.pdf [arquivo3.pdf ...]
```

### Opções

| Flag | Descrição |
|------|-----------|
| `-o` | Arquivo PDF de saída (obrigatório) |
| `--optimize` | Otimiza o PDF mesclado, reduzindo o tamanho |
| `--trim` | Mantém apenas as páginas selecionadas |
| `--pages` | Seleção de páginas para `--trim` (ex: `1-5`, `odd`, `even`, `1,3,7`) |

### Exemplos

```bash
# Mesclar PDFs
./pdfmerge -o documento_completo.pdf capitulo1.pdf capitulo2.pdf capitulo3.pdf

# Mesclar e otimizar
./pdfmerge -o saida.pdf --optimize a.pdf b.pdf

# Mesclar e manter apenas páginas ímpares
./pdfmerge -o saida.pdf --trim --pages odd a.pdf b.pdf

# Mesclar, manter páginas 1-10 e otimizar
./pdfmerge -o saida.pdf --trim --pages 1-10 --optimize a.pdf b.pdf
```

Os PDFs são mesclados na ordem em que são informados.
