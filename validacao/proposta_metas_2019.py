"""
Proposta de metas 2019 por Continente x Categoria.

As metas originais de 2019 são incoerentes com o histórico (ex.: Asia com meta
anual de R$ 2,3 Mi após faturar R$ 31,5 Mi em 2018). Este script calcula dois
cenários de meta e grava docs/proposta_metas_2019.csv.

Cenário Conservador  = Realizado 2018 x (1 + crescimento total da empresa 2018/2017)
Cenário Tendência    = Realizado 01/01-16/03/2019 / participação média desse mesmo
                       período no faturamento anual de 2017 e 2018 (anualização
                       do 1º trimestre com a sazonalidade histórica)

Uso:
    python validacao/proposta_metas_2019.py
"""
from pathlib import Path

import pandas as pd

from validacao import carregar

SAIDA = Path(__file__).resolve().parent.parent / "docs" / "proposta_metas_2019.csv"


def no_periodo_1t(datas):
    """Recorte comparável ao dado disponível de 2019: 01/01 a 16/03."""
    return (datas.dt.month < 3) | ((datas.dt.month == 3) & (datas.dt.day <= 16))


def main():
    v, m = carregar()
    chave = ["Continente", "Categoria"]

    anual = v[v.Ano < 2019].pivot_table(index=chave, columns="Ano", values="Valor Venda", aggfunc="sum")
    tri = v[no_periodo_1t(v["Data Venda"])].pivot_table(index=chave, columns="Ano", values="Valor Venda", aggfunc="sum")

    # Crescimento total da empresa 2018/2017
    cresc = anual[2018].sum() / anual[2017].sum() - 1
    # Participação média do período 01/01-16/03 no faturamento anual (2017 e 2018)
    part_1t = ((tri[2017].sum() / anual[2017].sum()) + (tri[2018].sum() / anual[2018].sum())) / 2

    meta_orig = m[m.Ano == 2019].set_index(chave)["Meta"]

    t = pd.DataFrame({
        "Realizado_2017": anual[2017],
        "Realizado_2018": anual[2018],
        "Realizado_2019_ate_16_03": tri[2019],
        "Meta_Original_2019": meta_orig,
    })
    t["Meta_Proposta_Conservadora"] = t["Realizado_2018"] * (1 + cresc)
    t["Meta_Proposta_Tendencia"] = t["Realizado_2019_ate_16_03"] / part_1t
    t["Var_Conservadora_vs_Original_%"] = (t["Meta_Proposta_Conservadora"] / t["Meta_Original_2019"] - 1) * 100

    t = t.round(2).reset_index()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(SAIDA, index=False, encoding="utf-8")

    print(f"Crescimento 2018/2017: {cresc:.2%} | participação média 01/01-16/03: {part_1t:.2%}")
    print(t.to_string(index=False))
    tot = t.select_dtypes("number").sum()
    print("\nTotais:", {k: round(tot[k], 2) for k in ["Realizado_2018", "Meta_Original_2019",
                                                       "Meta_Proposta_Conservadora", "Meta_Proposta_Tendencia"]})
    print("Arquivo gerado:", SAIDA)


if __name__ == "__main__":
    main()
