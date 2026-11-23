"""
Validação independente dos números do dashboard Vendas x Metas.

Reproduz em Python (pandas) o tratamento feito no Power Query e calcula
as respostas das perguntas do desafio, para conferência com o Power BI.

Uso:
    pip install pandas openpyxl
    python validacao/validacao.py
"""
from pathlib import Path
import json

import pandas as pd

DADOS = Path(__file__).resolve().parent.parent / "dados"


def carregar():
    # Vendas: cabeçalho na 6ª linha; Valor Venda líquido de desconto
    vendas = pd.read_excel(DADOS / "Vendas.xlsx", header=5)
    vendas["Valor Venda"] = vendas["Preço Unitário"] * vendas["Quantidade"] - vendas["Valor Desconto"]
    vendas["Ano"] = vendas["Data Venda"].dt.year

    # Subcategoria -> Categoria
    sub = pd.DataFrame(json.loads((DADOS / "Subcategoria.json").read_text(encoding="utf-8")))
    sub = sub.rename(columns={"idSubcategoria": "ID Subcategoria"})

    # Localização: continente vem como linha de agrupamento
    loc = pd.read_csv(DADOS / "Localizacao.csv", sep=";", skiprows=2, encoding="utf-8-sig")
    loc["Continente"] = loc["Tipo Localização"].where(loc["ID Localização"] == "Continente:").ffill()
    loc = loc[loc["Tipo Localização"] == "City"].copy()
    loc["ID Cidade"] = loc["ID Localização"].astype(int)

    cliente = pd.read_excel(DADOS / "Cliente.xlsx")[["ID Cliente", "ID Cidade"]]
    cliente = cliente.merge(loc[["ID Cidade", "Continente"]], on="ID Cidade", how="left")

    vendas = (vendas.drop(columns=["ID Cidade"])
                    .merge(sub, on="ID Subcategoria", how="left")
                    .merge(cliente[["ID Cliente", "Continente"]], on="ID Cliente", how="left"))

    # Metas: 3 abas em matriz Categoria x Continente
    metas = []
    for aba in ["2017", "2018", "2019"]:
        m = pd.read_excel(DADOS / "Metas.xlsx", sheet_name=aba, header=1).iloc[:3, :4]
        m.columns = ["Categoria", "Asia", "Europe", "North America"]
        m = m.melt("Categoria", var_name="Continente", value_name="Meta")
        m["Ano"] = int(aba)
        metas.append(m)
    metas = pd.concat(metas)
    metas["Meta"] = metas["Meta"].astype(float)
    return vendas, metas


def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v):
    return f"{v * 100:,.2f}%".replace(".", ",")


# Valores exibidos no dashboard Power BI (usados para conferência automática)
ESPERADO = {
    "faturamento_total": 171_377_435.74,
    "meta_proporcional": 165_350_068.16,
    "faturamento_2017": 67_197_712.59,
    "faturamento_2018": 85_470_908.87,
    "computers_total": 127_387_254.64,
    "desktops_europe_var_2018": -1_040_236.87,
}


def conferir(nome, obtido, esperado, tolerancia=0.01):
    ok = abs(obtido - esperado) <= tolerancia
    print(f"   [{'OK' if ok else 'ERRO'}] {nome}: {obtido:,.2f} (dashboard: {esperado:,.2f})")
    return ok


def main():
    v, m = carregar()
    ultima = v["Data Venda"].max()
    dias_2019 = (ultima - pd.Timestamp("2019-01-01")).days + 1
    meta_prop = m[m.Ano < 2019].Meta.sum() + m[m.Ano == 2019].Meta.sum() * dias_2019 / 365

    fat = v["Valor Venda"].sum()
    print("== EXPLORATÓRIA ==")
    print("1. Faturamento total:", brl(fat))
    print("2. Meta do período (proporcional até", ultima.date(), "):", brl(meta_prop),
          "| meta anual cheia:", brl(m.Meta.sum()))
    print("3. % atingimento:", pct(fat / meta_prop), "| sobre meta cheia:", pct(fat / m.Meta.sum()))
    cat = v.groupby("Categoria")["Valor Venda"].sum().sort_values(ascending=False)
    print("4. Categoria com maior faturamento:", cat.index[0], brl(cat.iloc[0]))
    print("5. Representatividade:", pct(cat.iloc[0] / fat))
    top3 = v.groupby("Subcategoria")["Valor Venda"].sum().nlargest(3)
    print("6. Top 3 subcategorias:", {k: brl(x) for k, x in top3.items()})
    cont = v[v.Subcategoria.isin(top3.index)].groupby("Continente")["Valor Venda"].sum().sort_values(ascending=False)
    print("7. Continentes (top 3 subcategorias):", {k: brl(x) for k, x in cont.items()})

    print("\n== COMPARATIVO 2018 x 2017 ==")
    a = v[v.Ano.isin([2017, 2018])]
    tot = a.groupby("Ano")["Valor Venda"].sum()
    print("8. Variação:", brl(tot[2018] - tot[2017]), pct(tot[2018] / tot[2017] - 1))
    sc = a.pivot_table(index="Subcategoria", columns="Ano", values="Valor Venda", aggfunc="sum")
    sc["var"] = sc[2018] / sc[2017] - 1
    neg = sc[sc["var"] < 0]
    print("9. Subcategorias com variação negativa:", {k: pct(x) for k, x in neg["var"].items()})
    r17 = sc.loc["Desktops", 2017] / tot[2017]
    r18 = sc.loc["Desktops", 2018] / tot[2018]
    pp = f"{(r18 - r17) * 100:.2f}".replace(".", ",")
    print(f"10. Representatividade Desktops: {pct(r17)} -> {pct(r18)} | variação {pp} p.p. ({pct(r18 / r17 - 1)} relativo)")
    d = a[a.Subcategoria == "Desktops"].pivot_table(index="Continente", columns="Ano", values="Valor Venda", aggfunc="sum")
    d["var"] = d[2018] - d[2017]
    print("11. Desktops por continente (var R$):", {k: brl(x) for k, x in d["var"].items()})
    c = a.pivot_table(index="Categoria", columns="Ano", values="Valor Venda", aggfunc="sum")
    print("12. Maior categoria 2018:", c[2018].idxmax(), brl(c[2018].max()))
    c["var"] = c[2018] / c[2017] - 1
    print("13. Maior variação %:", c["var"].idxmax(), pct(c["var"].max()))
    t18 = sc[2018].nlargest(3)
    print("14. Top 3 subcategorias 2018:", {k: brl(x) for k, x in t18.items()})
    print("15. Mesmas do período total?", list(t18.index) == list(top3.index))

    print("\n== CONFERÊNCIA COM O DASHBOARD ==")
    checks = [
        conferir("Faturamento total", fat, ESPERADO["faturamento_total"]),
        conferir("Meta proporcional", meta_prop, ESPERADO["meta_proporcional"]),
        conferir("Faturamento 2017", tot[2017], ESPERADO["faturamento_2017"]),
        conferir("Faturamento 2018", tot[2018], ESPERADO["faturamento_2018"]),
        conferir("Computers (período)", cat["Computers"], ESPERADO["computers_total"]),
        conferir("Desktops Europe var. 2018", d.loc["Europe", "var"], ESPERADO["desktops_europe_var_2018"]),
    ]
    if not all(checks):
        raise SystemExit("Divergência entre a validação e o dashboard.")
    print("Todos os valores conferem com o dashboard.")


if __name__ == "__main__":
    main()
