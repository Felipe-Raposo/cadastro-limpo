package main

// Códigos de saída do processo (os.Exit).
const (
	exitOK      = 0 // arquivo limpo ou sem achados
	exitSevere  = 1 // inválido XML 1.0, fora ASCII 32–126, Unicode não permitido ou reservado
	exitWarning = 2 // apenas achados leves (suspeitos)
)

// snippetRunesMax é o número máximo de runas exibidas no trecho de célula nos relatórios.
const snippetRunesMax = 40
