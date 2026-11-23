// =====================================================================
// Consultas Power Query (M) do relatório Vendas_x_Metas.pbix
// Cada bloco abaixo é uma consulta separada no Power Query.
// Consultas de apoio (sem carga no modelo): Subcategoria, Localizacao
// =====================================================================

// ---------- PastaDados (parâmetro) ----------
// Ajuste para a pasta onde estão os arquivos da pasta /dados
"C:\Users\Home\Desktop\DesafioDirecty\Requisitos\" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

// ---------- Subcategoria ----------
let
    Fonte = Json.Document(File.Contents(PastaDados & "Subcategoria.json")),
    Tabela = Table.FromRecords(Fonte),
    Renomeado = Table.RenameColumns(Tabela, {{"idSubcategoria", "ID Subcategoria"}}),
    Tipos = Table.TransformColumnTypes(Renomeado, {{"ID Subcategoria", Int64.Type}, {"Subcategoria", type text}, {"Categoria", type text}})
in
    Tipos

// ---------- Localizacao ----------
// O continente vem como linha de agrupamento ("Continente:;Asia") -> coluna + preencher para baixo
let
    Fonte = Csv.Document(File.Contents(PastaDados & "Localizacao.csv"), [Delimiter = ";", Columns = 5, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    RemoverTitulo = Table.Skip(Fonte, 2),
    Cabecalho = Table.PromoteHeaders(RemoverTitulo, [PromoteAllScalars = true]),
    AddContinente = Table.AddColumn(Cabecalho, "Continente", each if [ID Localização] = "Continente:" then [Tipo Localização] else null, type text),
    PreencherContinente = Table.FillDown(AddContinente, {"Continente"}),
    SoCidades = Table.SelectRows(PreencherContinente, each [Tipo Localização] = "City"),
    Renomeado = Table.RenameColumns(SoCidades, {{"ID Localização", "ID Cidade"}}),
    Colunas = Table.SelectColumns(Renomeado, {"ID Cidade", "Cidade", "Estado", "País", "Continente"}),
    Tipos = Table.TransformColumnTypes(Colunas, {{"ID Cidade", Int64.Type}, {"Cidade", type text}, {"Estado", type text}, {"País", type text}})
in
    Tipos

// ---------- dProduto ----------
// Marca vem como linha de agrupamento; ID e nome vêm concatenados ("Produto # 116 - ...")
let
    Fonte = Csv.Document(File.Contents(PastaDados & "Produto.csv"), [Delimiter = ";", Columns = 2, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    RemoverTitulo = Table.Skip(Fonte, 2),
    Cabecalho = Table.PromoteHeaders(RemoverTitulo, [PromoteAllScalars = true]),
    AddMarca = Table.AddColumn(Cabecalho, "Marca", each if [Produto] = "Marca:" then [Subcategoria] else null, type text),
    PreencherMarca = Table.FillDown(AddMarca, {"Marca"}),
    SoProdutos = Table.SelectRows(PreencherMarca, each Text.StartsWith([Produto], "Produto #")),
    IDProduto = Table.AddColumn(SoProdutos, "ID Produto", each Number.From(Text.BetweenDelimiters([Produto], "# ", " - ")), Int64.Type),
    NomeProduto = Table.AddColumn(IDProduto, "Nome Produto", each Text.AfterDelimiter([Produto], " - "), type text),
    IDSub = Table.AddColumn(NomeProduto, "ID Subcategoria", each Number.From(Text.BetweenDelimiters([Subcategoria], "# ", " - ")), Int64.Type),
    Colunas = Table.SelectColumns(IDSub, {"ID Produto", "Nome Produto", "Marca", "ID Subcategoria"}),
    Renomeado = Table.RenameColumns(Colunas, {{"Nome Produto", "Produto"}}),
    Mesclado = Table.NestedJoin(Renomeado, {"ID Subcategoria"}, Subcategoria, {"ID Subcategoria"}, "Sub", JoinKind.LeftOuter),
    Expandido = Table.ExpandTableColumn(Mesclado, "Sub", {"Subcategoria", "Categoria"})
in
    Expandido

// ---------- dCliente ----------
// Nome conforme o tipo (Person: nome + sobrenome | Company: nome da empresa) + localização
let
    Fonte = Excel.Workbook(File.Contents(PastaDados & "Cliente.xlsx"), null, true),
    Planilha = Fonte{[Item = "Cliente", Kind = "Sheet"]}[Data],
    Cabecalho = Table.PromoteHeaders(Planilha, [PromoteAllScalars = true]),
    TiposChave = Table.TransformColumnTypes(Cabecalho, {{"ID Cliente", Int64.Type}, {"ID Cidade", Int64.Type}}),
    AddNome = Table.AddColumn(TiposChave, "Nome", each if [Tipo Cliente] = "Company" then [Nome Empresa] else [Primeiro Nome] & " " & [Sobrenome], type text),
    Mesclado = Table.NestedJoin(AddNome, {"ID Cidade"}, Localizacao, {"ID Cidade"}, "Loc", JoinKind.LeftOuter),
    Expandido = Table.ExpandTableColumn(Mesclado, "Loc", {"Continente", "País", "Estado", "Cidade"}),
    Renomeado = Table.RenameColumns(Expandido, {{"Tipo Cliente", "Tipo"}}),
    Colunas = Table.SelectColumns(Renomeado, {"ID Cliente", "Tipo", "Nome", "Continente", "País", "Estado", "Cidade"}),
    Tipos = Table.TransformColumnTypes(Colunas, {{"Tipo", type text}, {"Continente", type text}, {"País", type text}, {"Estado", type text}, {"Cidade", type text}})
in
    Tipos

// ---------- fVendas ----------
// Pula as linhas de título; cria Valor Venda (líquido de desconto) e Valor Custo
let
    Fonte = Excel.Workbook(File.Contents(PastaDados & "Vendas.xlsx"), null, true),
    Planilha = Fonte{[Item = "Vendas", Kind = "Sheet"]}[Data],
    PularTitulo = Table.Skip(Planilha, each [Column1] <> "Data Venda"),
    Cabecalho = Table.PromoteHeaders(PularTitulo, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho, {{"Data Venda", type date}, {"Data Envio", type date}, {"ID Produto", Int64.Type}, {"ID Cliente", Int64.Type}, {"No. Venda", type text}, {"Custo Unitário", type number}, {"Preço Unitário", type number}, {"Quantidade", Int64.Type}, {"Valor Desconto", type number}}),
    AddValorVenda = Table.AddColumn(Tipos, "Valor Venda", each [Preço Unitário] * [Quantidade] - [Valor Desconto], type number),
    AddValorCusto = Table.AddColumn(AddValorVenda, "Valor Custo", each [Custo Unitário] * [Quantidade], type number),
    Final = Table.RemoveColumns(AddValorCusto, {"ID Subcategoria", "ID Cidade"})
in
    Final

// ---------- fMetas ----------
// 3 abas (2017, 2018, 2019) em matriz Categoria x Continente -> combinar + unpivot
let
    Fonte = Excel.Workbook(File.Contents(PastaDados & "Metas.xlsx"), null, true),
    Planilhas = Table.SelectRows(Fonte, each [Kind] = "Sheet"),
    TratarAba = (aba as table) as table =>
        let
            PularTitulo = Table.Skip(aba, each [Column2] <> "Asia"),
            Cabecalho = Table.PromoteHeaders(PularTitulo, [PromoteAllScalars = true]),
            PrimeiraColuna = Table.ColumnNames(Cabecalho){0},
            Renomeado = Table.RenameColumns(Cabecalho, {{PrimeiraColuna, "Categoria"}}),
            SemTotal = Table.SelectRows(Renomeado, each [Categoria] <> null and [Categoria] <> "Total"),
            Unpivot = Table.UnpivotOtherColumns(SemTotal, {"Categoria"}, "Continente", "Valor Meta")
        in
            Unpivot,
    Tratadas = Table.AddColumn(Planilhas, "Dados", each TratarAba([Data])),
    AddAno = Table.AddColumn(Tratadas, "Ano", each Number.From([Item]), Int64.Type),
    Colunas = Table.SelectColumns(AddAno, {"Ano", "Dados"}),
    Expandido = Table.ExpandTableColumn(Colunas, "Dados", {"Categoria", "Continente", "Valor Meta"}),
    AddData = Table.AddColumn(Expandido, "Data", each #date([Ano], 1, 1), type date),
    Tipos = Table.TransformColumnTypes(AddData, {{"Categoria", type text}, {"Continente", type text}, {"Valor Meta", type number}}),
    Final = Table.SelectColumns(Tipos, {"Data", "Continente", "Categoria", "Valor Meta"})
in
    Final

// ---------- dCategoria (dimensão ponte: filtra dProduto e fMetas) ----------
let
    Fonte = Table.Distinct(Table.SelectColumns(Subcategoria, {"Categoria"}))
in
    Fonte

// ---------- dContinente (dimensão ponte: filtra dCliente e fMetas) ----------
let
    Fonte = Table.Distinct(Table.SelectColumns(Localizacao, {"Continente"}))
in
    Fonte
