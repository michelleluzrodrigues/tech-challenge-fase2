from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import pandas as pd
import time

# Iniciar o WebDriver diretamente, sem especificar o caminho completo
driver = webdriver.Chrome()

# Navegar até a página desejada
url = 'https://sistemaswebb3-listados.b3.com.br/indexPage/day/ibov?language=pt-br'  # Substitua pela URL real da página
driver.get(url)

# Selecionar a opção "Setor de Atuação"
select_element = Select(driver.find_element(By.ID, 'segment'))
select_element.select_by_visible_text('Setor de Atuação')

# Esperar a página carregar os dados
time.sleep(2)

# Função para extrair dados de uma página
def extract_data():
    try:
        table = driver.find_element(By.XPATH, '//table[@class="table table-responsive-sm table-responsive-md"]')
        tbody = table.find_element(By.TAG_NAME, 'tbody')
        rows = tbody.find_elements(By.TAG_NAME, 'tr')
        page_data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, 'td')
            cols = [col.text for col in cols]
            if len(cols) == 7:  # Certifique-se de que cada linha tenha exatamente 7 colunas
                page_data.append(cols)
            else:
                print(f"Linha ignorada devido ao número incorreto de colunas: {cols}")
        return page_data
    except Exception as e:
        print(f"Erro ao extrair dados: {e}")
        return []

all_data = []

while True:
    page_data = extract_data()
    if not page_data:
        break
    all_data.extend(page_data)
    
    try:
        next_button = driver.find_element(By.XPATH, '//li[@class="pagination-next"]/a')
        next_button.click()
        time.sleep(2)  # Esperar um pouco para a próxima página carregar
    except:
        break

# Verificar se os dados foram extraídos corretamente
if not all_data:
    print("Nenhum dado foi extraído. Verifique os XPaths e a estrutura da tabela.")
else:
    columns = ['Setor', 'Código', 'Ação', 'Tipo', 'Qtde. Teórica', 'Part. (%)', 'Part. (%)Acum.']
    df = pd.DataFrame(all_data, columns=columns)

    # Salvar os dados em um arquivo CSV (opcional)
    df.to_csv('carteira_do_dia_completa.csv', index=False)

    print("Dados extraídos e salvos com sucesso:")
    print(df)

# Fechar o WebDriver
driver.quit()