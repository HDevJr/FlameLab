// Gerado a partir de data/ (parametros, evidencias, lacunas, documentos) de BASS2-M1. Nao editar a mao.
window.FL_DATA = {
 "doc": {
  "id": "NASA-TM-20210011385",
  "title": "Burning and Suppression of Solids—II (BASS—II) Summary Report",
  "url": "https://ntrs.nasa.gov/citations/20210011385",
  "sha256": "5ffa911fd9b6356f204646003fb9342e341810dcdfdf5cb15756e7f01ec5f770",
  "version": "October 2021 (conforme folha de rosto do PDF)"
 },
 "params": [
  {
   "id": "BASS2-M1.material",
   "key": "material",
   "label": "Material",
   "labelSource": null,
   "role": "METADADO",
   "status": "CONFERIDO_FONTE",
   "value": "PMMA (polimetilmetacrilato; \"clear cast\")",
   "unit": null,
   "si": null,
   "refs": [
    {
     "id": "EV-TM20210011385-S53-p56-M1-material",
     "page": 56,
     "pdfIndex": 64,
     "section": "5.3",
     "table": null,
     "row": null,
     "column": null,
     "precision": "PAGE",
     "quote": "A total of 20 PMMA flat samples were burnt during the BASS-II experimentation (Table 5.1)."
    },
    {
     "id": "EV-TM20210011385-S51-p55-M1-material",
     "page": 55,
     "pdfIndex": 63,
     "section": "5.1",
     "table": null,
     "row": null,
     "column": null,
     "precision": "PAGE",
     "quote": "Combustion of clear cast polymethylmethacrylate (PMMA) samples ..."
    }
   ],
   "caveats": [
    "A Tabela 5.1 não tem coluna de material; a identificação vem do texto da §5.3 (as 20 amostras planas da Tabela 5.1 são de PMMA) e da §5.1 (\"clear cast PMMA\")."
   ],
   "reviewer": "Junior",
   "reviewedAt": "2026-11-15T02:52:36Z"
  },
  {
   "id": "BASS2-M1.thickness",
   "key": "thickness",
   "label": "Espessura da amostra",
   "labelSource": "Thickness, mm",
   "role": "CONDICAO",
   "status": "CONFERIDO_FONTE",
   "value": 1,
   "unit": "mm",
   "si": {
    "value": 0.001,
    "unit": "m"
   },
   "refs": [
    {
     "id": "EV-TM20210011385-T51-M1-thickness",
     "page": 57,
     "pdfIndex": 65,
     "section": "5.3",
     "table": "5.1",
     "row": "M1",
     "column": "Thickness, mm",
     "precision": "TABLE_CELL",
     "quote": "TABLE 5.1. TWENTY BURNING AND SUPPRESSION OF SOLIDS-II (BASS-II) TESTS | Test no. M1 | Thickness, mm: 1"
    }
   ],
   "caveats": [],
   "reviewer": "Junior",
   "reviewedAt": "2026-11-15T02:51:26Z"
  },
  {
   "id": "BASS2-M1.width",
   "key": "width",
   "label": "Largura da amostra",
   "labelSource": "Width, cm",
   "role": "CONDICAO",
   "status": "CONFERIDO_FONTE",
   "value": 2.2,
   "unit": "cm",
   "si": {
    "value": 0.022000000000000002,
    "unit": "m"
   },
   "refs": [
    {
     "id": "EV-TM20210011385-T51-M1-width",
     "page": 57,
     "pdfIndex": 65,
     "section": "5.3",
     "table": "5.1",
     "row": "M1",
     "column": "Width, cm",
     "precision": "TABLE_CELL",
     "quote": "TABLE 5.1. TWENTY BURNING AND SUPPRESSION OF SOLIDS-II (BASS-II) TESTS | Test no. M1 | Width, cm: 2.2"
    }
   ],
   "caveats": [
    "Divergência interna da fonte: o texto das §5.1 (p. 55) e §5.3 (p. 56) menciona larguras de \"1 or 2 cm\", enquanto a Tabela 5.1 e o texto da p. 58 listam 1,2 e 2,2 cm. Valor da tabela registrado; divergência a avaliar na revisão."
   ],
   "reviewer": "Junior",
   "reviewedAt": "2026-11-15T02:51:36Z"
  },
  {
   "id": "BASS2-M1.burning_faces",
   "key": "burning_faces",
   "label": "Faces em combustão",
   "labelSource": "One or two sides burning",
   "role": "CONDICAO",
   "status": "CONFERIDO_FONTE",
   "value": 1,
   "unit": null,
   "si": {
    "value": 1.0,
    "unit": "adimensional"
   },
   "refs": [
    {
     "id": "EV-TM20210011385-T51-M1-faces",
     "page": 57,
     "pdfIndex": 65,
     "section": "5.3",
     "table": "5.1",
     "row": "M1",
     "column": "One or two sides burning",
     "precision": "TABLE_CELL",
     "quote": "TABLE 5.1. TWENTY BURNING AND SUPPRESSION OF SOLIDS-II (BASS-II) TESTS | Test no. M1 | One or two sides burning: 1"
    }
   ],
   "caveats": [
    "Coluna \"One or two sides burning\" = 1 (queima em uma face)."
   ],
   "reviewer": "Junior",
   "reviewedAt": "2026-11-15T02:51:49Z"
  },
  {
   "id": "BASS2-M1.airflow_velocity",
   "key": "airflow_velocity",
   "label": "Velocidade do ar (escoamento oposto)",
   "labelSource": "Velocity, cm/s",
   "role": "CONDICAO",
   "status": "CONFERIDO_FONTE",
   "value": 9,
   "unit": "cm/s",
   "si": {
    "value": 0.09,
    "unit": "m/s"
   },
   "refs": [
    {
     "id": "EV-TM20210011385-T51-M1-flow",
     "page": 57,
     "pdfIndex": 65,
     "section": "5.3",
     "table": "5.1",
     "row": "M1",
     "column": "Velocity, cm/s",
     "precision": "TABLE_CELL",
     "quote": "TABLE 5.1. TWENTY BURNING AND SUPPRESSION OF SOLIDS-II (BASS-II) TESTS | Test no. M1 | Velocity, cm/s: 9"
    }
   ],
   "caveats": [
    "Valor tabulado único para M1; não descreve o perfil espacial nem a variação temporal."
   ],
   "reviewer": "Junior",
   "reviewedAt": "2026-11-15T02:51:58Z"
  },
  {
   "id": "BASS2-M1.flame_spread_rate",
   "key": "flame_spread_rate",
   "label": "Velocidade de propagação da chama",
   "labelSource": "Spread rate, mm/s",
   "role": "OBSERVAVEL",
   "status": "CONFERIDO_FONTE",
   "value": 0.071,
   "unit": "mm/s",
   "si": {
    "value": 7.099999999999999e-05,
    "unit": "m/s"
   },
   "refs": [
    {
     "id": "EV-TM20210011385-T51-M1-spread",
     "page": 57,
     "pdfIndex": 65,
     "section": "5.3",
     "table": "5.1",
     "row": "M1",
     "column": "Spread rate, mm/s",
     "precision": "TABLE_CELL",
     "quote": "TABLE 5.1. TWENTY BURNING AND SUPPRESSION OF SOLIDS-II (BASS-II) TESTS | Test no. M1 | Spread rate, mm/s: 0.071"
    }
   ],
   "caveats": [
    "RESULTADO OBSERVADO: nunca usar como entrada ou alvo de calibração de modelo.",
    "Obtida por rastreamento de imagens/vídeo (§5.1, §5.3); incerteza não informada."
   ],
   "reviewer": "Junior",
   "reviewedAt": "2026-11-15T02:52:12Z"
  },
  {
   "id": "BASS2-M1.burn_duration",
   "key": "burn_duration",
   "label": "Tempo de queima",
   "labelSource": "Burn time, min",
   "role": "OBSERVAVEL",
   "status": "CONFERIDO_FONTE",
   "value": 6.4,
   "unit": "min",
   "si": {
    "value": 384.0,
    "unit": "s"
   },
   "refs": [
    {
     "id": "EV-TM20210011385-T51-M1-burntime",
     "page": 57,
     "pdfIndex": 65,
     "section": "5.3",
     "table": "5.1",
     "row": "M1",
     "column": "Burn time, min",
     "precision": "TABLE_CELL",
     "quote": "TABLE 5.1. TWENTY BURNING AND SUPPRESSION OF SOLIDS-II (BASS-II) TESTS | Test no. M1 | Burn time, min: 6.4"
    }
   ],
   "caveats": [
    "Duração reportada; não implica regime estacionário."
   ],
   "reviewer": "Junior",
   "reviewedAt": "2026-11-15T02:52:19Z"
  },
  {
   "id": "BASS2-M1.o2_initial",
   "key": "o2_initial",
   "label": "Concentração inicial de O₂",
   "labelSource": "Initial O2, vol%",
   "role": "CONDICAO",
   "status": "CONFERIDO_FONTE",
   "value": 22.2,
   "unit": "vol%",
   "si": {
    "value": 0.222,
    "unit": "fraction"
   },
   "refs": [
    {
     "id": "EV-TM20210011385-T51-M1-o2i",
     "page": 57,
     "pdfIndex": 65,
     "section": "5.3",
     "table": "5.1",
     "row": "M1",
     "column": "Initial O2, vol%",
     "precision": "TABLE_CELL",
     "quote": "TABLE 5.1. TWENTY BURNING AND SUPPRESSION OF SOLIDS-II (BASS-II) TESTS | Test no. M1 | Initial O2, vol%: 22.2"
    }
   ],
   "caveats": [
    "Base volumétrica (vol%) declarada no cabeçalho da Tabela 5.1.",
    "O₂ medido apenas no início e no fim do ensaio; os autores assumem perfil linear entre os dois pontos (§5.4, p. 60)."
   ],
   "reviewer": "Junior",
   "reviewedAt": "2026-11-15T02:52:04Z"
  },
  {
   "id": "BASS2-M1.o2_final",
   "key": "o2_final",
   "label": "Concentração final de O₂",
   "labelSource": "Final O2, vol%",
   "role": "OBSERVAVEL",
   "status": "CONFERIDO_FONTE",
   "value": 21.9,
   "unit": "vol%",
   "si": {
    "value": 0.219,
    "unit": "fraction"
   },
   "refs": [
    {
     "id": "EV-TM20210011385-T51-M1-o2f",
     "page": 57,
     "pdfIndex": 65,
     "section": "5.3",
     "table": "5.1",
     "row": "M1",
     "column": "Final O2, vol%",
     "precision": "TABLE_CELL",
     "quote": "TABLE 5.1. TWENTY BURNING AND SUPPRESSION OF SOLIDS-II (BASS-II) TESTS | Test no. M1 | Final O2, vol%: 21.9"
    }
   ],
   "caveats": [
    "O₂ medido apenas no início e no fim; não é concentração constante durante o ensaio (§5.4, p. 60)."
   ],
   "reviewer": "Junior",
   "reviewedAt": "2026-11-15T02:52:28Z"
  }
 ],
 "gaps": [
  {
   "key": "sample_length",
   "label": "Comprimento da amostra",
   "blocks": [
    "FDS_REPRODUCTION"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.1–§5.7 (p. 55–63; PDF 63–71)",
    "Tabela 5.1 (p. 57)"
   ],
   "why": "A Tabela 5.1 não informa o comprimento da amostra de M1.",
   "maybe": "A §5.1 (p. 55) traz uma afirmação geral sobre o comprimento das amostras do conjunto, não específica de M1. Candidata a registro somente após revisão humana."
  },
  {
   "key": "sample_holder_substrate",
   "label": "Suporte e substrato metálico da amostra",
   "blocks": [
    "FDS_REPRODUCTION"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.1–§5.7 (p. 55–63; PDF 63–71)"
   ],
   "why": "O texto da p. 58 menciona perda de calor para o substrato metálico em amostras de uma face e para o porta-amostra, sem material, dimensões ou posição.",
   "maybe": "Referências 7, 8, 10 e 11 do capítulo 5 (teses e artigos da SDSU) — a investigar."
  },
  {
   "key": "duct_geometry",
   "label": "Dimensões efetivas do duto",
   "blocks": [
    "FDS_REPRODUCTION"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.3 (p. 56)",
    "§5.5 (p. 60–61)"
   ],
   "why": "A §5.3 descreve um \"small flow duct\" sem dimensões; a §5.5 informa que o modelo histórico usou geometria \"approximate\" do duto.",
   "maybe": "Figuras 5.1 e 5.6 (imagens não analisadas nesta etapa) e Ref. 3/4 do capítulo 5."
  },
  {
   "key": "ambient_pressure",
   "label": "Pressão",
   "blocks": [
    "FDS_REPRODUCTION"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.1–§5.7 (p. 55–63; PDF 63–71)"
   ],
   "why": "Nenhuma pressão é informada para M1 no capítulo 5.",
   "maybe": "Outros capítulos do relatório e dados do PSI-25 — a investigar."
  },
  {
   "key": "ambient_temperature",
   "label": "Temperatura ambiente/inicial",
   "blocks": [
    "FDS_REPRODUCTION"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.1–§5.7 (p. 55–63; PDF 63–71)"
   ],
   "why": "Nenhuma temperatura do gás ou da amostra é informada para M1 no capítulo 5.",
   "maybe": "Outros capítulos do relatório e dados do PSI-25 — a investigar."
  },
  {
   "key": "inlet_flow_profile",
   "label": "Perfil espacial e temporal do escoamento de entrada",
   "blocks": [
    "FDS_REPRODUCTION"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.3 (p. 56)",
    "§5.5 (p. 60)"
   ],
   "why": "A §5.5 informa que o perfil foi medido em vários pontos e é \"quite irregular\", mas os valores não estão no relatório.",
   "maybe": "Dados brutos do anemômetro no PSI-25 — a investigar."
  },
  {
   "key": "anemometer_location",
   "label": "Posição de medição do anemômetro",
   "blocks": [
    "FDS_REPRODUCTION"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.3 (p. 56)"
   ],
   "why": "A §5.3 informa apenas que o anemômetro mede o ar que entra no duto; a posição exata não é dada.",
   "maybe": "Documentação do hardware BASS (Ref. 3 do capítulo 5) — a investigar."
  },
  {
   "key": "ignition_procedure",
   "label": "Procedimento, duração e fonte de ignição",
   "blocks": [
    "FDS_REPRODUCTION"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.3 (p. 56)",
    "§5.5 (p. 61)"
   ],
   "why": "A §5.3 menciona o ignitor e a estabilização da chama, sem potência nem duração para M1. A duração de ignição citada na §5.5 refere-se ao MODELO numérico, não ao experimento.",
   "maybe": "Documentação do hardware BASS — a investigar."
  },
  {
   "key": "pmma_pyrolysis_properties",
   "label": "Propriedades termoquímicas e de pirólise do PMMA",
   "blocks": [
    "FDS_REPRODUCTION"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.1–§5.7 (p. 55–63; PDF 63–71)"
   ],
   "why": "O capítulo 5 não lista propriedades do PMMA; os autores afirmam que precisam modificar a cinética química e as propriedades do material para melhorar o modelo (§5.1, §5.7).",
   "maybe": "Outros capítulos trazem propriedades usadas em análises de OUTRAS geometrias (amostras cilíndricas); não transferir para M1 sem revisão científica."
  },
  {
   "key": "o2_time_profile",
   "label": "Perfil temporal do O₂ durante o ensaio",
   "blocks": [
    "FDS_REPRODUCTION"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.4 (p. 60)"
   ],
   "why": "A §5.4 informa que o O₂ só foi medido no início e no fim; o perfil intermediário é uma suposição linear dos autores, não uma medição.",
   "maybe": null
  },
  {
   "key": "measurement_uncertainty",
   "label": "Incertezas de medição",
   "blocks": [
    "FDS_REPRODUCTION",
    "QUANTITATIVE_COMPARISON"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.1–§5.7 (p. 55–63; PDF 63–71)"
   ],
   "why": "Não há incertezas declaradas para os valores de M1 na Tabela 5.1 nem no texto do capítulo 5.",
   "maybe": "Referências 9–11 do capítulo 5 — a investigar."
  },
  {
   "key": "flame_front_tracking_method",
   "label": "Método de cálculo do avanço da frente de chama",
   "blocks": [
    "QUANTITATIVE_COMPARISON"
   ],
   "searched": [
    "NASA-TM-20210011385 §5.1 (p. 55)",
    "§5.3 (p. 56)"
   ],
   "why": "Parcial: imagens e vídeos foram rastreados com software de rastreamento de imagens da NASA e os dados processados em planilha (§5.3); critério de frente, janela de ajuste e incerteza não são descritos.",
   "maybe": "Ref. 6 do capítulo 5 (software de rastreamento) e teses da SDSU — a investigar."
  }
 ]
};
