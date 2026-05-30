# sanitiser

Atualiza um **Excel (.xlsx)** com:

1. **Dados cadastrais** a partir da coluna configurada em `sanitiser.entity.cpf_cnpj_column`: só dígitos são considerados; **11 dígitos** disparam a API em `entity.cpf`, **14 dígitos** disparam `entity.cnpj`.
2. **Endereço** a partir do CEP na coluna `sanitiser.address.cep_column`, usando a API em `address.api.url` (placeholder `{cep}` com 8 dígitos).

No **arquivo de saída**, células recebem preenchimento sólido: **verde claro** onde o valor foi **alterado** ao gravar dados vindos do JSON (mapeamentos `response_to_column` de CPF, CNPJ ou CEP); **amarelo claro** na coluna de documento (CPF/CNPJ) ou na coluna de CEP quando a consulta à API falha (o mesmo caso que gera aviso no log). O ajuste de espaços em `text_columns` não é destacado em verde.

O leiaute segue o modelo de [`layout.morador.json`](../layout.morador.json) (bloco `sanitiser`).

## Uso

```bash
cd tools
pip install -e .

sanitiser entrada.xlsx -l layout.morador.json -o saida.xlsx
sanitiser entrada.xlsx -l layout.morador.json -o saida.xlsx --lines 100
sanitiser entrada.xlsx -l layout.morador.json -o saida.xlsx --http-timeout 60
sanitiser entrada.xlsx -l layout.morador.json -o saida.xlsx --no-cache
sanitiser entrada.xlsx -l layout.morador.json -o saida.xlsx --cache-db /caminho/cache.sqlite
```

### Timeout, retentativas e cache

- **Timeout HTTP** (`--http-timeout SEC`): tempo máximo por requisição às APIs (padrão: 30 segundos).
- **Retentativas**: em falhas consideradas transitórias (timeout de leitura, erros de conexão comuns, **toda a família HTTP 4xx** (400–499), HTTP 502/503/504), cada consulta é repetida até **3 vezes**, com espera **0,5 s → 1 s → 2 s** entre tentativas.
- **Fim da planilha**: timeout na leitura do corpo HTTP passa a gerar **aviso por linha** (como os demais erros de API) e o processo **continua** até salvar o `.xlsx` de saída; não encerra mais o programa inteiro com `sanitiser: The read operation timed out`.
- **Cache SQLite**: respostas **HTTP 4xx** **não** são gravadas; após esgotar as retentativas, a próxima execução tenta de novo. Ao abrir o cache, entradas antigas de erro **HTTP 4xx** são removidas. Erros **definitivos** de outro tipo (JSON inválido, `success=false`, HTTP 5xx após retentativas, etc.) podem ser gravados para não refazer a mesma chamada. Falhas transitórias esgotadas sem sucesso **não** são gravadas.

Consultas CPF/CNPJ/CEP são gravadas em SQLite para não repetir HTTP na mesma chave e mesma URL/headers do leiaute. Por padrão o cache fica na **pasta de cache do usuário**, oculta conforme a convenção de cada sistema:

- **Windows**: `%LOCALAPPDATA%\Cadastro Limpo\api_cache.sqlite`
- **macOS**: `~/Library/Caches/Cadastro Limpo/api_cache.sqlite`
- **Linux**: `${XDG_CACHE_HOME:-~/.cache}/cadastro-limpo/api_cache.sqlite`

Na primeira execução, a pasta é criada e populada a partir do sqlite embarcado ([`sanitiser/data/api_cache.sqlite`](sanitiser/data/api_cache.sqlite), versionado no repositório como seed). Para usar outro arquivo: `--cache-db /caminho/cache.sqlite`.

Módulo:

```bash
PYTHONPATH=. python -m sanitiser entrada.xlsx -l layout.morador.json -o saida.xlsx
```

## Leiaute (`sanitiser`)

- `entity.cpf_cnpj_column`: letra da coluna com CPF ou CNPJ.
- `entity.cpf` / `entity.cnpj`: cada um com `api.url` (`{cpf}` ou `{cnpj}`), `api.headers` opcional, e `response_to_column` (chaves do JSON → letras de coluna; `null` ignora).
- `address` (opcional): `cep_column`, `api.url` com `{cep}`, `response_to_column` (ex.: ViaCEP: `logradouro`, `bairro`, `localidade`). Na coluna mapeada para **`logradouro`**, só o texto **antes da primeira vírgula** é substituído pelo retorno da API; tudo após essa vírgula (complemento, inclusive outras vírgulas) permanece na célula.

Nomes em mapeamentos de entidade (`NOME`, `NOME_MAE`, `razao_social`, etc.) são gravados em **maiúsculas**; `SEXO` e `NASC` (CPF) seguem a resposta da API; campos de endereço seguem o texto retornado.

## Dependências

`openpyxl` (mesmo `pyproject.toml` em `tools/`). HTTP via biblioteca padrão do Python.
