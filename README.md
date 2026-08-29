# 🛡️ M1TOS EC • Cartola FC Optimizer Pro

Otimizador matemático de alta performance para o Cartola FC utilizando **Programação Linear Inteira Mista (MILP)**, modelagem de **Pontuação Esperada ($xP$)**, **Fator Momento**, **Matriz de Cedência de Scouts** e suporte completo à nova regra de **Reserva de Luxo**.

---

## 🚀 Funcionalidades Principais

- 🏟️ **Interface Web Interativa (Streamlit)**: Dashboard moderno e responsivo (Desktop & Mobile) com visualização em cards táticos, fotos dos atletas, escudos dos clubes e badges de destaque.
- 🎯 **Motor Estatístico de Pontuação Esperada ($xP$)**:
  - **Fator Momento**: Ponderação do desempenho nos últimos 5 confrontos com pesos exponenciais.
  - **Matriz de Cedência de Scouts**: Cruzamento de fragilidades defensivas, faltas cometidas e finalizações cedidas pelos adversários.
  - **Cálculo Realista de SG**: Modelagem de probabilidade de *Clean Sheet* por confronto.
- 👑 **Capitão Integrado no Solver Linear**: Otimização do multiplicador $1.5\times$ diretamente na função objetivo matemática.
- 📋 **Seleção Automática da Melhor Formação**: Avalia simultaneamente `4-3-3`, `4-4-2`, `3-4-3`, `3-5-2` e `5-3-2` escolhendo a de maior retorno esperado.
- ⭐ **Reserva de Luxo Oficial**: Identificação do melhor reserva da rodada com maior teto (*upside*) e ganho esperado na substituição automática.
- 📊 **Exportação Multiformato**: Geração automática de planilhas CSV e imagens PNG de alta resolução.

---

## 🛠️ Instalação e Configuração

1. **Clonar o repositório:**
   ```bash
   git clone <URL_DO_REPOSITORIO>
   cd cartola_bot
   ```

2. **Criar e ativar o ambiente virtual:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instalar as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🖥️ Como Executar

### 1. Interface Web (Recomendado ⭐)
Abra o dashboard interativo no seu navegador:
```bash
streamlit run app.py
```
> Acesse em `http://localhost:8501` ou use o link de rede local exibido no terminal para acessar pelo celular na mesma rede Wi-Fi!

### 2. Terminal Interativo (CLI)
Basta rodar o comando principal e responder às perguntas com valores pré-definidos:
```bash
python main.py
```

### 3. Terminal com Parâmetros
```bash
# Busca com orçamento personalizado e melhor formação automática
python main.py -b 146.07 -f auto

# Busca com formação fixa e limite de atletas por clube
python main.py -b 135.0 -f 4-3-3 --max-per-club 4
```

---

## ⚙️ Estrutura do Projeto

```text
├── app.py                  # Dashboard Web Interativo (Streamlit)
├── main.py                 # Ponto de entrada CLI e terminal interativo
├── requirements.txt        # Dependências do projeto
├── cartola_bot/
│   ├── api.py             # Cliente resiliente da API oficial do Cartola FC
│   ├── scoring.py         # Motor de métricas (xP, Fator Momento, Cedência)
│   ├── solver.py          # Otimizador matemático MILP (PuLP)
│   ├── exporter.py        # Exportação Rich, CSV e Imagens PNG
│   └── config.yaml        # Configurações de pesos, regras e formações
├── cache/                 # Cache local de dados da API
└── exports/               # Escalações exportadas (CSV e Imagens PNG)
```

---

© 2026 **M1TOS EC** • Powered by MILP Optimization & AI

