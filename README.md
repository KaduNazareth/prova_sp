# Prova Paulista – API Consumer

Script Python para autenticação, consumo e exportação dos dados da API da Prova Paulista.

## Pré-requisitos

- Python 3.10 ou superior
- pip

## Instalação

```bash
# 1. Clone ou copie a pasta do projeto e acesse-a
cd prova_paulista

# 2. Crie e ative o ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux

# 3. Instale as dependências
pip install -r requirements.txt
```

## Configuração

Crie um arquivo chamado .env na raiz do projeto com base no .env.example:

```
KID=seu_kid_aqui
TOKEN=seu_token_aqui
```

As credenciais (KID e TOKEN) que foram fornecidas via e-mail.

## Execução

```bash
python script.py
```

O script irá:
1. Autenticar na API e obter um Bearer Token JWT
2. Consumir todos os registros de forma paginada
3. Normalizar e estruturar os dados
4. Exportar o arquivo `output/prova_paulista.csv`

## Saída

O arquivo CSV gerado em `output/prova_paulista.csv` contém as seguintes colunas:

| Coluna       | Descrição                                      |
|--------------|------------------------------------------------|
| `id_escola`  | Identificador único da escola                  |
| `escola`     | Nome da escola                                 |
| `ano`        | Ano de referência dos dados                    |
| `nota_geral` | Nota geral da escola (escala 0–100)            |
| `nota_1`     | Nota da 1ª Prova Paulista (escala 0–100)       |
| `nota_2`     | Nota da 2ª Prova Paulista (escala 0–100)       |
| `nota_3`     | Nota da 3ª Prova Paulista (escala 0–100)       |

O separador utilizado é `;` para compatibilidade com o Excel em português.